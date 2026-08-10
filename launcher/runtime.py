from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import BinaryIO


class LauncherError(RuntimeError):
    """An expected launcher or service-management failure."""


class ServiceKind(StrEnum):
    DATABASE = "database"
    SERVER = "server"
    SIDECAR = "sidecar"
    WORLD = "world"


class ServicePhase(StrEnum):
    STOPPED = "stopped"
    STARTING = "starting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FOREIGN = "port conflict"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ServiceSpec:
    service_id: str
    display_name: str
    kind: ServiceKind
    executable: Path
    arguments: tuple[str, ...]
    working_directory: Path
    port: int
    startup_timeout_seconds: int
    stdout_log: Path
    stderr_log: Path
    health_url: str | None = None
    stdin_pipe: bool = False
    graceful_stop_command: str | None = None
    admin_executable: Path | None = None
    password_file: Path | None = None

    @property
    def command(self) -> tuple[str, ...]:
        return (str(self.executable), *self.arguments)


@dataclass(frozen=True, slots=True)
class LauncherConfig:
    server_root: Path
    refresh_seconds: int
    startup_order: tuple[str, ...]
    services: dict[str, ServiceSpec]


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service_id: str
    phase: ServicePhase
    port: int
    pid: int | None = None
    process_path: str | None = None
    detail: str = ""


@dataclass(slots=True)
class ManagedProcess:
    process: subprocess.Popen[str]
    stdout_handle: BinaryIO
    stderr_handle: BinaryIO

    def close_logs(self) -> None:
        self.stdout_handle.close()
        self.stderr_handle.close()


def discover_server_root(start: Path) -> Path:
    """Find the organized runtime root from a launcher or test path."""
    for candidate in (start.resolve(), *start.resolve().parents):
        if (candidate / "bin/mangosd.exe").is_file() and (
            candidate / "config/mangosd.conf"
        ).is_file():
            return candidate
    raise LauncherError(f"could not find server root above {start}")


def _resolve_inside(root: Path, value: str, label: str) -> Path:
    candidate = (root / value).resolve()
    if not candidate.is_relative_to(root):
        raise LauncherError(f"{label} escapes the server root: {value}")
    return candidate


def load_config(path: Path, server_root: Path | None = None) -> LauncherConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LauncherError(f"cannot load launcher configuration: {exc}") from exc

    root = (server_root or discover_server_root(path.parent)).resolve()
    service_rows = raw.get("services")
    if not isinstance(service_rows, dict) or not service_rows:
        raise LauncherError("configuration requires at least one service")

    services: dict[str, ServiceSpec] = {}
    used_ports: set[int] = set()
    for service_id, row in service_rows.items():
        try:
            port = int(row["port"])
            if not 1 <= port <= 65535 or port in used_ports:
                raise ValueError("port must be unique and between 1 and 65535")
            used_ports.add(port)
            arguments = tuple(
                str(argument).replace("{root}", root.as_posix())
                for argument in row.get("arguments", [])
            )
            admin_value = row.get("admin_executable")
            password_value = row.get("password_file")
            services[service_id] = ServiceSpec(
                service_id=service_id,
                display_name=str(row["display_name"]),
                kind=ServiceKind(row["kind"]),
                executable=_resolve_inside(root, row["executable"], "executable"),
                arguments=arguments,
                working_directory=_resolve_inside(
                    root, row.get("working_directory", "."), "working_directory"
                ),
                port=port,
                startup_timeout_seconds=int(row.get("startup_timeout_seconds", 30)),
                stdout_log=_resolve_inside(root, row["stdout_log"], "stdout_log"),
                stderr_log=_resolve_inside(root, row["stderr_log"], "stderr_log"),
                health_url=row.get("health_url"),
                stdin_pipe=bool(row.get("stdin_pipe", False)),
                graceful_stop_command=row.get("graceful_stop_command"),
                admin_executable=(
                    _resolve_inside(root, admin_value, "admin_executable")
                    if admin_value
                    else None
                ),
                password_file=(
                    _resolve_inside(root, password_value, "password_file")
                    if password_value
                    else None
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise LauncherError(f"invalid service {service_id!r}: {exc}") from exc

    order = tuple(raw.get("startup_order", services))
    if set(order) != set(services) or len(order) != len(services):
        raise LauncherError("startup_order must contain every service exactly once")
    refresh = int(raw.get("refresh_seconds", 2))
    if not 1 <= refresh <= 60:
        raise LauncherError("refresh_seconds must be between 1 and 60")
    return LauncherConfig(root, refresh, order, services)


def parse_netstat_listeners(output: str) -> dict[int, set[int]]:
    """Return TCP listener PIDs grouped by local port."""
    listeners: dict[int, set[int]] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 5 or fields[0].upper() != "TCP" or fields[3].upper() != "LISTENING":
            continue
        match = re.search(r":(\d+)$", fields[1])
        if not match:
            continue
        try:
            port = int(match.group(1))
            pid = int(fields[4])
        except ValueError:
            continue
        listeners.setdefault(port, set()).add(pid)
    return listeners


def tcp_listeners() -> dict[int, set[int]]:
    result = subprocess.run(
        ["netstat", "-ano", "-p", "TCP"],
        capture_output=True,
        text=True,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode:
        raise LauncherError(f"netstat failed with exit code {result.returncode}")
    return parse_netstat_listeners(result.stdout)


def process_image_path(pid: int) -> str | None:
    if os.name != "nt":
        return None
    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return None
    try:
        size = ctypes.c_ulong(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if ctypes.windll.kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value
        return None
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _terminate_pid(pid: int) -> None:
    if os.name != "nt":
        raise LauncherError("this launcher currently supports Windows only")
    process_terminate = 0x0001
    handle = ctypes.windll.kernel32.OpenProcess(process_terminate, False, pid)
    if not handle:
        raise LauncherError(f"cannot open PID {pid} for termination")
    try:
        if not ctypes.windll.kernel32.TerminateProcess(handle, 0):
            raise LauncherError(f"could not terminate PID {pid}")
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def tail_text(path: Path, max_lines: int = 200, max_bytes: int = 256_000) -> str:
    if not path.exists():
        return f"{path.name} has not been created yet."
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - max_bytes))
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    return "\n".join(text.splitlines()[-max_lines:])


class ServiceSupervisor:
    def __init__(self, config: LauncherConfig) -> None:
        self.config = config
        self._managed: dict[str, ManagedProcess] = {}
        self._allowed_images: dict[str, set[Path]] = {}
        self._lock = threading.RLock()

    def validate_files(self, service_id: str) -> None:
        spec = self.config.services[service_id]
        required = [spec.executable, spec.working_directory]
        if spec.admin_executable:
            required.append(spec.admin_executable)
        if spec.password_file:
            required.append(spec.password_file)
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            raise LauncherError("missing required path(s): " + ", ".join(missing))
        self._allowed_process_images(spec)

    def snapshot(self) -> dict[str, ServiceStatus]:
        listeners = tcp_listeners()
        with self._lock:
            self._reap_finished()
            return {
                service_id: self._status_for(spec, listeners)
                for service_id, spec in self.config.services.items()
            }

    def _status_for(
        self, spec: ServiceSpec, listeners: dict[int, set[int]]
    ) -> ServiceStatus:
        pids = sorted(listeners.get(spec.port, set()))
        if not pids:
            managed = self._managed.get(spec.service_id)
            if managed and managed.process.poll() is None:
                return ServiceStatus(
                    spec.service_id,
                    ServicePhase.STARTING,
                    spec.port,
                    managed.process.pid,
                    str(spec.executable),
                    "process is running; waiting for its listener",
                )
            return ServiceStatus(spec.service_id, ServicePhase.STOPPED, spec.port)

        expected_pid: int | None = None
        expected_path: str | None = None
        for pid in pids:
            image = process_image_path(pid)
            if image and self._image_matches(spec, image):
                expected_pid, expected_path = pid, image
                break
        if expected_pid is None:
            pid = pids[0]
            image = process_image_path(pid)
            return ServiceStatus(
                spec.service_id,
                ServicePhase.FOREIGN,
                spec.port,
                pid,
                image,
                "port is owned by an unexpected executable",
            )

        if spec.health_url:
            try:
                with urllib.request.urlopen(spec.health_url, timeout=1.5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if response.status != 200 or payload.get("status") != "ready":
                    return ServiceStatus(
                        spec.service_id,
                        ServicePhase.DEGRADED,
                        spec.port,
                        expected_pid,
                        expected_path,
                        "listener is up but readiness failed",
                    )
            except (OSError, ValueError, urllib.error.URLError):
                return ServiceStatus(
                    spec.service_id,
                    ServicePhase.DEGRADED,
                    spec.port,
                    expected_pid,
                    expected_path,
                    "listener is up but health endpoint is unavailable",
                )
        return ServiceStatus(
            spec.service_id,
            ServicePhase.HEALTHY,
            spec.port,
            expected_pid,
            expected_path,
            "ready",
        )

    def start(self, service_id: str) -> int:
        spec = self.config.services[service_id]
        current = self.snapshot()[service_id]
        if current.phase in (ServicePhase.HEALTHY, ServicePhase.DEGRADED):
            return current.pid or 0
        if current.phase == ServicePhase.FOREIGN:
            raise LauncherError(f"cannot start {spec.display_name}: port {spec.port} is in use")
        if current.phase == ServicePhase.STARTING:
            return current.pid or 0
        self.validate_files(service_id)
        spec.stdout_log.parent.mkdir(parents=True, exist_ok=True)
        spec.stderr_log.parent.mkdir(parents=True, exist_ok=True)
        stdout_handle = spec.stdout_log.open("ab", buffering=0)
        stderr_handle = spec.stderr_log.open("ab", buffering=0)
        try:
            process = subprocess.Popen(
                spec.command,
                cwd=spec.working_directory,
                stdin=subprocess.PIPE if spec.stdin_pipe else subprocess.DEVNULL,
                stdout=stdout_handle,
                stderr=stderr_handle,
                text=spec.stdin_pipe,
                creationflags=(
                    getattr(subprocess, "CREATE_NO_WINDOW", 0)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                ),
            )
        except OSError as exc:
            stdout_handle.close()
            stderr_handle.close()
            raise LauncherError(f"could not start {spec.display_name}: {exc}") from exc
        with self._lock:
            self._managed[service_id] = ManagedProcess(process, stdout_handle, stderr_handle)
        return process.pid

    def wait_until_ready(self, service_id: str) -> ServiceStatus:
        spec = self.config.services[service_id]
        deadline = time.monotonic() + spec.startup_timeout_seconds
        last = self.snapshot()[service_id]
        while time.monotonic() < deadline:
            last = self.snapshot()[service_id]
            if last.phase == ServicePhase.HEALTHY:
                return last
            if last.phase in (ServicePhase.FAILED, ServicePhase.FOREIGN, ServicePhase.STOPPED):
                break
            time.sleep(0.5)
        raise LauncherError(
            f"{spec.display_name} did not become ready: {last.phase.value} {last.detail}".strip()
        )

    def start_all(self) -> None:
        for service_id in self.config.startup_order:
            self.start(service_id)
            self.wait_until_ready(service_id)

    def stop_all(self) -> None:
        errors: list[str] = []
        for service_id in reversed(self.config.startup_order):
            try:
                self.stop(service_id)
            except LauncherError as exc:
                errors.append(str(exc))
        if errors:
            raise LauncherError("; ".join(errors))

    def restart(self, service_id: str) -> None:
        self.stop(service_id)
        self.start(service_id)
        self.wait_until_ready(service_id)

    def stop(self, service_id: str) -> None:
        spec = self.config.services[service_id]
        status = self.snapshot()[service_id]
        if status.phase == ServicePhase.STOPPED:
            return
        if status.phase == ServicePhase.FOREIGN:
            raise LauncherError(
                f"refusing to stop PID {status.pid}: port {spec.port} belongs to another executable"
            )

        managed = self._managed.get(service_id)
        if spec.kind == ServiceKind.DATABASE:
            self._stop_database(spec)
        elif managed and managed.process.poll() is None:
            self._stop_managed(spec, managed)
        elif status.pid:
            image = process_image_path(status.pid)
            if not image or not self._image_matches(spec, image):
                raise LauncherError(f"refusing to stop unverified PID {status.pid}")
            _terminate_pid(status.pid)

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.snapshot()[service_id].phase == ServicePhase.STOPPED:
                return
            time.sleep(0.25)
        raise LauncherError(f"{spec.display_name} did not stop within 20 seconds")

    def _stop_managed(self, spec: ServiceSpec, managed: ManagedProcess) -> None:
        process = managed.process
        if spec.graceful_stop_command and process.stdin:
            try:
                process.stdin.write(spec.graceful_stop_command + "\n")
                process.stdin.flush()
                process.wait(timeout=15)
                return
            except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                pass
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _stop_database(self, spec: ServiceSpec) -> None:
        if not spec.admin_executable or not spec.password_file:
            raise LauncherError("database shutdown is not configured")
        password = spec.password_file.read_text(encoding="utf-8").strip()
        if not password:
            raise LauncherError("database password file is empty")
        environment = os.environ.copy()
        environment["MYSQL_PWD"] = password
        try:
            result = subprocess.run(
                [
                    str(spec.admin_executable),
                    "--host=127.0.0.1",
                    f"--port={spec.port}",
                    "--user=root",
                    "shutdown",
                ],
                cwd=spec.working_directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        finally:
            environment.pop("MYSQL_PWD", None)
            password = ""
        if result.returncode:
            error = result.stderr.strip() or f"exit code {result.returncode}"
            raise LauncherError(f"MariaDB shutdown failed: {error}")

    def managed_service_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(
                service_id
                for service_id, managed in self._managed.items()
                if managed.process.poll() is None
            )

    def service_log(self, service_id: str, max_lines: int = 220) -> str:
        spec = self.config.services[service_id]
        stdout = tail_text(spec.stdout_log, max_lines=max_lines)
        stderr = tail_text(spec.stderr_log, max_lines=max_lines // 2)
        return f"[{spec.stdout_log.name}]\n{stdout}\n\n[{spec.stderr_log.name}]\n{stderr}"

    def _allowed_process_images(self, spec: ServiceSpec) -> set[Path]:
        cached = self._allowed_images.get(spec.service_id)
        if cached is not None:
            return cached
        images = {spec.executable.resolve()}
        if spec.kind == ServiceKind.SIDECAR and spec.executable.exists():
            result = subprocess.run(
                [
                    str(spec.executable),
                    "-c",
                    "import sys; print(sys._base_executable)",
                ],
                cwd=spec.working_directory,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode or not result.stdout.strip():
                raise LauncherError("could not identify the sidecar base Python executable")
            base_python = Path(result.stdout.strip()).resolve()
            if base_python.name.casefold() not in {"python.exe", "pythonw.exe"}:
                raise LauncherError("sidecar base executable is not Python")
            images.add(base_python)
        self._allowed_images[spec.service_id] = images
        return images

    def _image_matches(self, spec: ServiceSpec, image: str | Path) -> bool:
        return any(_same_path(image, expected) for expected in self._allowed_process_images(spec))

    def _reap_finished(self) -> None:
        finished = [
            service_id
            for service_id, managed in self._managed.items()
            if managed.process.poll() is not None
        ]
        for service_id in finished:
            self._managed.pop(service_id).close_logs()

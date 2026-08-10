from __future__ import annotations

import json
from pathlib import Path

import pytest
from launcher.runtime import (
    LauncherError,
    ServiceKind,
    discover_server_root,
    load_config,
    parse_netstat_listeners,
    tail_text,
)


def make_runtime_root(tmp_path: Path) -> Path:
    (tmp_path / "bin").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "bin/mangosd.exe").touch()
    (tmp_path / "config/mangosd.conf").touch()
    return tmp_path


def test_discovers_runtime_root(tmp_path: Path) -> None:
    root = make_runtime_root(tmp_path)
    nested = root / "dev/launcher"
    nested.mkdir(parents=True)
    assert discover_server_root(nested) == root


def test_parses_ipv4_and_ipv6_listeners() -> None:
    output = """
      TCP    0.0.0.0:8090       0.0.0.0:0       LISTENING       1200
      TCP    [::]:3306          [::]:0          LISTENING       1300
      TCP    127.0.0.1:8100     127.0.0.1:52000 ESTABLISHED     1400
    """
    assert parse_netstat_listeners(output) == {8090: {1200}, 3306: {1300}}


def test_tail_text_is_bounded(tmp_path: Path) -> None:
    log = tmp_path / "service.log"
    log.write_text("\n".join(f"line {value}" for value in range(20)), encoding="utf-8")
    assert tail_text(log, max_lines=3) == "line 17\nline 18\nline 19"


def test_load_config_renders_root_and_service_kind(tmp_path: Path) -> None:
    root = make_runtime_root(tmp_path)
    config_path = root / "dev/launcher/config.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "startup_order": ["world"],
                "services": {
                    "world": {
                        "display_name": "World",
                        "kind": "world",
                        "executable": "bin/mangosd.exe",
                        "arguments": ["-c", "{root}/config/mangosd.conf"],
                        "working_directory": ".",
                        "port": 8090,
                        "stdout_log": "logs/out.log",
                        "stderr_log": "logs/err.log"
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    config = load_config(config_path, root)
    spec = config.services["world"]
    assert spec.kind == ServiceKind.WORLD
    assert spec.arguments[1] == f"{root.as_posix()}/config/mangosd.conf"


def test_rejects_paths_outside_runtime_root(tmp_path: Path) -> None:
    root = make_runtime_root(tmp_path)
    path = root / "launcher.json"
    path.write_text(
        json.dumps(
            {
                "startup_order": ["bad"],
                "services": {
                    "bad": {
                        "display_name": "Bad",
                        "kind": "server",
                        "executable": "../outside.exe",
                        "port": 1234,
                        "stdout_log": "logs/out.log",
                        "stderr_log": "logs/err.log"
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LauncherError, match="escapes the server root"):
        load_config(path, root)


def test_rejects_duplicate_ports(tmp_path: Path) -> None:
    root = make_runtime_root(tmp_path)
    row = {
        "display_name": "Service",
        "kind": "server",
        "executable": "bin/mangosd.exe",
        "port": 8090,
        "stdout_log": "logs/out.log",
        "stderr_log": "logs/err.log"
    }
    path = root / "launcher.json"
    path.write_text(
        json.dumps(
            {
                "startup_order": ["one", "two"],
                "services": {"one": row, "two": {**row, "display_name": "Two"}}
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LauncherError, match="port must be unique"):
        load_config(path, root)

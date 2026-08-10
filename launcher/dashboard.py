from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any

from launcher.runtime import (
    LauncherConfig,
    LauncherError,
    ServicePhase,
    ServiceStatus,
    ServiceSupervisor,
)

COLORS = {
    ServicePhase.STOPPED: "#747b8a",
    ServicePhase.STARTING: "#e0a82e",
    ServicePhase.HEALTHY: "#3fb950",
    ServicePhase.DEGRADED: "#d29922",
    ServicePhase.FOREIGN: "#f85149",
    ServicePhase.FAILED: "#f85149",
}


class Dashboard(tk.Tk):
    def __init__(self, config: LauncherConfig) -> None:
        super().__init__()
        self.config_data = config
        self.supervisor = ServiceSupervisor(config)
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.cards: dict[str, dict[str, Any]] = {}
        self.refresh_running = False
        self.operation_running = False
        self.title("Tortoise WoW Server Dashboard")
        self.geometry("1120x760")
        self.minsize(900, 620)
        self.configure(background="#0d1117")
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._configure_style()
        self._build_ui()
        self.after(100, self._drain_events)
        self.after(150, self.refresh_status)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#161b22", foreground="#e6edf3", font=("Segoe UI", 10))
        style.configure("TFrame", background="#0d1117")
        style.configure("Card.TFrame", background="#161b22", relief="solid", borderwidth=1)
        style.configure("TLabel", background="#161b22", foreground="#e6edf3")
        style.configure("Header.TLabel", background="#0d1117", font=("Segoe UI Semibold", 20))
        style.configure("Muted.TLabel", background="#0d1117", foreground="#8b949e")
        style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 13))
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background="#238636", foreground="white")
        style.map("Accent.TButton", background=[("active", "#2ea043")])
        style.configure("Danger.TButton", background="#da3633", foreground="white")
        style.map("Danger.TButton", background=[("active", "#f85149")])
        style.configure("TNotebook", background="#0d1117", borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#161b22",
            foreground="#8b949e",
            padding=(14, 7),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#30363d")],
            foreground=[("selected", "#f0f6fc")],
        )
        style.configure(
            "TCombobox",
            fieldbackground="#0d1117",
            background="#21262d",
            foreground="#e6edf3",
            arrowcolor="#e6edf3",
        )

    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(22, 18, 22, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Tortoise WoW", style="Header.TLabel").pack(side="left")
        self.summary_var = tk.StringVar(value="Checking services…")
        ttk.Label(header, textvariable=self.summary_var, style="Muted.TLabel").pack(
            side="left", padx=(18, 0), pady=(8, 0)
        )
        ttk.Button(header, text="Open Logs", command=self._open_logs).pack(side="right")
        ttk.Button(header, text="Refresh", command=self.refresh_status).pack(
            side="right", padx=(0, 8)
        )

        actions = ttk.Frame(self, padding=(22, 0, 22, 14))
        actions.pack(fill="x")
        self.start_all_button = ttk.Button(
            actions, text="Start All", style="Accent.TButton", command=self._start_all
        )
        self.start_all_button.pack(side="left")
        self.stop_all_button = ttk.Button(
            actions, text="Stop All", style="Danger.TButton", command=self._stop_all
        )
        self.stop_all_button.pack(side="left", padx=8)
        ttk.Label(
            actions,
            text=f"Runtime root: {self.config_data.server_root}",
            style="Muted.TLabel",
        ).pack(side="right", pady=(8, 0))

        cards_frame = ttk.Frame(self, padding=(22, 0, 22, 12))
        cards_frame.pack(fill="x")
        for column, service_id in enumerate(self.config_data.startup_order):
            cards_frame.columnconfigure(column, weight=1, uniform="service")
            self._build_card(cards_frame, service_id, column)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=22, pady=(0, 18))
        log_tab = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        activity_tab = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        notebook.add(log_tab, text="Service logs")
        notebook.add(activity_tab, text="Launcher activity")

        log_controls = ttk.Frame(log_tab)
        log_controls.pack(fill="x", pady=(0, 8))
        ttk.Label(log_controls, text="Service").pack(side="left")
        self.log_service = tk.StringVar(value=self.config_data.startup_order[-1])
        selector = ttk.Combobox(
            log_controls,
            textvariable=self.log_service,
            values=self.config_data.startup_order,
            state="readonly",
            width=18,
        )
        selector.pack(side="left", padx=8)
        selector.bind("<<ComboboxSelected>>", lambda _: self._refresh_log())
        ttk.Button(log_controls, text="Reload", command=self._refresh_log).pack(side="left")

        self.log_text = tk.Text(
            log_tab,
            background="#010409",
            foreground="#c9d1d9",
            insertbackground="white",
            font=("Cascadia Mono", 9),
            wrap="none",
            relief="flat",
        )
        self.log_text.pack(fill="both", expand=True)
        self.activity_text = tk.Text(
            activity_tab,
            background="#010409",
            foreground="#c9d1d9",
            insertbackground="white",
            font=("Cascadia Mono", 9),
            wrap="word",
            relief="flat",
        )
        self.activity_text.pack(fill="both", expand=True)
        self._activity("Dashboard initialized")

    def _build_card(self, parent: ttk.Frame, service_id: str, column: int) -> None:
        spec = self.config_data.services[service_id]
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 6, 0))
        ttk.Label(card, text=spec.display_name, style="CardTitle.TLabel").pack(anchor="w")
        status_label = tk.Label(
            card,
            text="CHECKING",
            background="#747b8a",
            foreground="white",
            font=("Segoe UI Semibold", 9),
            padx=8,
            pady=3,
        )
        status_label.pack(anchor="w", pady=(10, 7))
        detail_var = tk.StringVar(value=f"Port {spec.port}")
        ttk.Label(card, textvariable=detail_var, foreground="#8b949e").pack(anchor="w")
        buttons = ttk.Frame(card, style="Card.TFrame")
        buttons.pack(fill="x", pady=(12, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        start_button = ttk.Button(
            buttons, text="Start", command=lambda sid=service_id: self._service_action(sid, "start")
        )
        start_button.grid(row=0, column=0, sticky="ew", padx=(0, 3))
        stop_button = ttk.Button(
            buttons, text="Stop", command=lambda sid=service_id: self._service_action(sid, "stop")
        )
        stop_button.grid(row=0, column=1, sticky="ew", padx=(3, 0))
        restart_button = ttk.Button(
            buttons,
            text="Restart",
            command=lambda sid=service_id: self._service_action(sid, "restart"),
        )
        restart_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.cards[service_id] = {
            "status": status_label,
            "detail": detail_var,
            "buttons": (start_button, stop_button, restart_button),
        }

    def refresh_status(self) -> None:
        if self.refresh_running:
            return
        self.refresh_running = True

        def worker() -> None:
            try:
                self.events.put(("snapshot", self.supervisor.snapshot()))
            except Exception as exc:  # noqa: BLE001 - UI boundary
                self.events.put(("error", f"Status refresh failed: {exc}"))
            finally:
                self.events.put(("refresh_done", None))

        threading.Thread(target=worker, daemon=True).start()

    def _service_action(self, service_id: str, action: str) -> None:
        def operation() -> None:
            spec = self.config_data.services[service_id]
            self.events.put(("activity", f"{action.title()} {spec.display_name}"))
            if action == "start":
                self.supervisor.start(service_id)
                self.supervisor.wait_until_ready(service_id)
            elif action == "stop":
                self.supervisor.stop(service_id)
            else:
                self.supervisor.restart(service_id)

        self._run_operation(operation)

    def _start_all(self) -> None:
        self._run_operation(self.supervisor.start_all, "Starting complete stack")

    def _stop_all(self) -> None:
        if not messagebox.askyesno(
            "Stop server stack?", "Stop the world, sidecar, realm server, and database?"
        ):
            return
        self._run_operation(self.supervisor.stop_all, "Stopping complete stack")

    def _run_operation(self, operation: Callable[[], None], label: str | None = None) -> None:
        if self.operation_running:
            messagebox.showinfo(
                "Operation in progress", "Wait for the current operation to finish."
            )
            return
        self.operation_running = True
        self._set_buttons_enabled(False)
        if label:
            self._activity(label)

        def worker() -> None:
            try:
                operation()
                self.events.put(("activity", "Operation completed"))
            except Exception as exc:  # noqa: BLE001 - UI boundary
                self.events.put(("operation_error", str(exc)))
            finally:
                self.events.put(("operation_done", None))

        threading.Thread(target=worker, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "snapshot":
                    self._apply_snapshot(payload)
                elif event == "activity":
                    self._activity(payload)
                elif event == "error":
                    self._activity(payload)
                elif event == "operation_error":
                    self._activity(f"ERROR: {payload}")
                    messagebox.showerror("Launcher operation failed", payload)
                elif event == "operation_done":
                    self.operation_running = False
                    self._set_buttons_enabled(True)
                    self.refresh_status()
                elif event == "refresh_done":
                    self.refresh_running = False
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _apply_snapshot(self, snapshot: dict[str, ServiceStatus]) -> None:
        healthy = 0
        for service_id, status in snapshot.items():
            card = self.cards[service_id]
            label: tk.Label = card["status"]
            label.configure(text=status.phase.value.upper(), background=COLORS[status.phase])
            if status.phase == ServicePhase.HEALTHY:
                healthy += 1
            pid_text = f" · PID {status.pid}" if status.pid else ""
            detail = status.detail or "not running"
            card["detail"].set(f"Port {status.port}{pid_text}\n{detail}")
        self.summary_var.set(f"{healthy}/{len(snapshot)} services ready")
        self._refresh_log()
        self.after(self.config_data.refresh_seconds * 1000, self.refresh_status)

    def _refresh_log(self) -> None:
        try:
            text = self.supervisor.service_log(self.log_service.get())
        except (LauncherError, OSError) as exc:
            text = f"Unable to read logs: {exc}"
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _activity(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activity_text.insert("end", f"[{timestamp}] {message}\n")
        self.activity_text.see("end")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.start_all_button.configure(state=state)
        self.stop_all_button.configure(state=state)
        for card in self.cards.values():
            for button in card["buttons"]:
                button.configure(state=state)

    def _open_logs(self) -> None:
        try:
            os.startfile(self.config_data.server_root / "logs")  # type: ignore[attr-defined]
        except OSError as exc:
            messagebox.showerror("Cannot open logs", str(exc))

    def _on_close(self) -> None:
        managed = self.supervisor.managed_service_ids()
        if managed:
            names = ", ".join(self.config_data.services[item].display_name for item in managed)
            if not messagebox.askyesno(
                "Stop managed services?",
                f"The dashboard owns: {names}.\n\nStop them cleanly and exit?",
            ):
                return

            def stop_and_exit() -> None:
                try:
                    self.supervisor.stop_all()
                except LauncherError as exc:
                    self.events.put(("activity", f"Shutdown warning: {exc}"))
                self.after(0, self.destroy)

            threading.Thread(target=stop_and_exit, daemon=True).start()
            return
        self.destroy()

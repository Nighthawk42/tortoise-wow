from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from launcher.runtime import LauncherError, ServiceSupervisor, load_config  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tortoise WoW server dashboard")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("config.json"),
        help="launcher configuration file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate configuration and print service status without opening the dashboard",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="start and verify a fully stopped stack, then stop it cleanly",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = load_config(args.config)
        supervisor = ServiceSupervisor(config)
        for service_id in config.services:
            supervisor.validate_files(service_id)
        if args.check:
            for service_id, status in supervisor.snapshot().items():
                pid = status.pid if status.pid is not None else "-"
                print(
                    f"{service_id:10} {status.phase.value:13} "
                    f"port={status.port:<5} pid={pid} {status.detail}".rstrip()
                )
            return 0
        if args.smoke:
            initial = supervisor.snapshot()
            active = [
                service_id
                for service_id, status in initial.items()
                if status.phase.value != "stopped"
            ]
            if active:
                raise LauncherError(
                    "smoke test requires a fully stopped stack; active: " + ", ".join(active)
                )
            try:
                supervisor.start_all()
                for service_id, status in supervisor.snapshot().items():
                    print(
                        f"READY {service_id} port={status.port} pid={status.pid or '-'}"
                    )
            finally:
                supervisor.stop_all()
            print("Smoke test completed; all services stopped cleanly.")
            return 0
        from launcher.dashboard import Dashboard

        Dashboard(config).mainloop()
        return 0
    except LauncherError as exc:
        print(f"Launcher error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

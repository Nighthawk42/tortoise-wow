from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    config_dir: Path
    server_id: str = "turtle-dev"
    provider: str = "mock"
    service_token: str | None = None

    @classmethod
    def from_environment(cls) -> Settings:
        default_config = Path(__file__).resolve().parents[1] / "config"
        configured_dir = os.getenv("TORTOISE_SIDECAR_CONFIG_DIR")
        token = os.getenv("TORTOISE_SIDECAR_SERVICE_TOKEN") or None
        return cls(
            config_dir=Path(configured_dir).resolve() if configured_dir else default_config,
            server_id=os.getenv("TORTOISE_SIDECAR_SERVER_ID", "turtle-dev"),
            provider=os.getenv("TORTOISE_SIDECAR_PROVIDER", "mock"),
            service_token=token,
        )


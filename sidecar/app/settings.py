from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True, slots=True)
class Settings:
    config_dir: Path
    server_id: str = "turtle-dev"
    provider: str = "mock"
    service_token: str | None = None
    provider_api_base: str | None = None
    provider_api_key: str | None = None
    provider_model_override: str | None = None
    provider_timeout_seconds: float = 12.0
    provider_max_concurrency: int = 4
    provider_requests_per_minute: int = 20
    provider_http_referer: str | None = None
    provider_app_title: str = "Tortoise WoW AI Players"

    @classmethod
    def from_environment(cls) -> Settings:
        sidecar_root = Path(__file__).resolve().parents[1]
        configured_env_file = os.getenv("TORTOISE_SIDECAR_ENV_FILE")
        env_file = (
            Path(configured_env_file).resolve() if configured_env_file else sidecar_root / ".env"
        )
        file_values = dotenv_values(env_file) if env_file.is_file() else {}

        def value(name: str, default: str | None = None) -> str | None:
            if name in os.environ:
                return os.environ[name]
            configured = file_values.get(name)
            return configured if configured is not None else default

        default_config = sidecar_root / "config"
        configured_dir = value("TORTOISE_SIDECAR_CONFIG_DIR")
        token = value("TORTOISE_SIDECAR_SERVICE_TOKEN") or None
        provider = (value("TORTOISE_SIDECAR_PROVIDER", "mock") or "mock").casefold()
        configured_api_base = value("TORTOISE_LLM_API_BASE") or None
        if provider == "openrouter" and configured_api_base is None:
            configured_api_base = "https://openrouter.ai/api/v1"
        api_key = value("TORTOISE_LLM_API_KEY") or None
        if provider == "openrouter" and api_key is None:
            api_key = value("OPENROUTER_API_KEY") or None
        return cls(
            config_dir=Path(configured_dir).resolve() if configured_dir else default_config,
            server_id=value("TORTOISE_SIDECAR_SERVER_ID", "turtle-dev") or "turtle-dev",
            provider=provider,
            service_token=token,
            provider_api_base=configured_api_base.rstrip("/") if configured_api_base else None,
            provider_api_key=api_key,
            provider_model_override=value("TORTOISE_LLM_MODEL") or None,
            provider_timeout_seconds=float(value("TORTOISE_LLM_TIMEOUT_SECONDS", "12") or "12"),
            provider_max_concurrency=int(value("TORTOISE_LLM_MAX_CONCURRENCY", "4") or "4"),
            provider_requests_per_minute=int(
                value("TORTOISE_LLM_REQUESTS_PER_MINUTE", "20") or "20"
            ),
            provider_http_referer=value("TORTOISE_LLM_HTTP_REFERER") or None,
            provider_app_title=value("TORTOISE_LLM_APP_TITLE", "Tortoise WoW AI Players")
            or "Tortoise WoW AI Players",
        )

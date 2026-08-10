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
        default_config = Path(__file__).resolve().parents[1] / "config"
        configured_dir = os.getenv("TORTOISE_SIDECAR_CONFIG_DIR")
        token = os.getenv("TORTOISE_SIDECAR_SERVICE_TOKEN") or None
        provider = os.getenv("TORTOISE_SIDECAR_PROVIDER", "mock").casefold()
        configured_api_base = os.getenv("TORTOISE_LLM_API_BASE") or None
        if provider == "openrouter" and configured_api_base is None:
            configured_api_base = "https://openrouter.ai/api/v1"
        api_key = os.getenv("TORTOISE_LLM_API_KEY") or None
        if provider == "openrouter" and api_key is None:
            api_key = os.getenv("OPENROUTER_API_KEY") or None
        return cls(
            config_dir=Path(configured_dir).resolve() if configured_dir else default_config,
            server_id=os.getenv("TORTOISE_SIDECAR_SERVER_ID", "turtle-dev"),
            provider=provider,
            service_token=token,
            provider_api_base=configured_api_base.rstrip("/") if configured_api_base else None,
            provider_api_key=api_key,
            provider_model_override=os.getenv("TORTOISE_LLM_MODEL") or None,
            provider_timeout_seconds=float(os.getenv("TORTOISE_LLM_TIMEOUT_SECONDS", "12")),
            provider_max_concurrency=int(os.getenv("TORTOISE_LLM_MAX_CONCURRENCY", "4")),
            provider_requests_per_minute=int(os.getenv("TORTOISE_LLM_REQUESTS_PER_MINUTE", "20")),
            provider_http_referer=os.getenv("TORTOISE_LLM_HTTP_REFERER") or None,
            provider_app_title=os.getenv("TORTOISE_LLM_APP_TITLE", "Tortoise WoW AI Players"),
        )

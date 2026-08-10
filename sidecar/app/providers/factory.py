from __future__ import annotations

from app.models.providers import ProviderRoutes
from app.providers.base import DialogueProvider, ProviderConfigurationError
from app.providers.mock import MockDialogueProvider
from app.providers.openai_compatible import OpenAICompatibleDialogueProvider
from app.settings import Settings


def create_provider(settings: Settings) -> DialogueProvider:
    if settings.provider == "mock":
        return MockDialogueProvider()
    if settings.provider not in {"openrouter", "openai-compatible"}:
        raise ProviderConfigurationError(f"unsupported provider {settings.provider!r}")
    if settings.provider == "openrouter" and not settings.provider_api_key:
        raise ProviderConfigurationError("OPENROUTER_API_KEY or TORTOISE_LLM_API_KEY is required")
    if settings.provider_api_base is None:
        raise ProviderConfigurationError("TORTOISE_LLM_API_BASE is required")
    try:
        routes = ProviderRoutes.load(settings.config_dir / "providers.yaml")
    except ValueError as exc:
        raise ProviderConfigurationError(str(exc)) from exc
    return OpenAICompatibleDialogueProvider(
        name=settings.provider,
        api_base=settings.provider_api_base,
        api_key=settings.provider_api_key,
        routes=routes,
        model_override=settings.provider_model_override,
        timeout_seconds=settings.provider_timeout_seconds,
        max_concurrency=settings.provider_max_concurrency,
        requests_per_minute=settings.provider_requests_per_minute,
        http_referer=settings.provider_http_referer,
        app_title=settings.provider_app_title,
    )

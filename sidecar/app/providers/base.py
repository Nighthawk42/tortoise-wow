from __future__ import annotations

from typing import Protocol

from app.models.api import DialogueRequest
from app.models.personas import ResolvedPersona


class DialogueProvider(Protocol):
    name: str

    async def generate(self, request: DialogueRequest, persona: ResolvedPersona) -> str: ...

    async def aclose(self) -> None: ...

    def metrics_snapshot(self) -> dict[str, int | float]: ...


class ProviderError(Exception):
    retryable = True


class ProviderConfigurationError(ProviderError):
    retryable = False


class ProviderRateLimitError(ProviderError):
    pass


class ProviderInvalidOutputError(ProviderError):
    retryable = False

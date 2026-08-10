from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from app.models.api import (
    DialogueCandidate,
    DialogueError,
    DialogueRequest,
    DialogueResponse,
    ErrorCode,
    MemorySummary,
    OutcomeRequest,
    PersonaReference,
)
from app.personas.registry import PersonaRegistry, RegistryError
from app.providers.base import (
    DialogueProvider,
    ProviderError,
    ProviderInvalidOutputError,
    ProviderRateLimitError,
)


class DialogueService:
    def __init__(self, registry: PersonaRegistry, provider: DialogueProvider) -> None:
        self.registry = registry
        self.provider = provider
        self._responses: dict[tuple[str, UUID], DialogueResponse] = {}
        self._outcomes: dict[tuple[str, UUID], OutcomeRequest] = {}
        self._lock = asyncio.Lock()

    async def dialogue(self, request: DialogueRequest) -> DialogueResponse:
        key = (request.server_id, request.request_id)
        async with self._lock:
            if cached := self._responses.get(key):
                return cached

        if request.deadline <= datetime.now(UTC):
            return await self._remember_failure(request, ErrorCode.DEADLINE_EXPIRED)

        try:
            persona = self.registry.resolve(request)
        except RegistryError as exc:
            return await self._remember_failure(request, exc.code)

        try:
            remaining = (request.deadline - datetime.now(UTC)).total_seconds()
            async with asyncio.timeout(max(remaining, 0)):
                text = await self.provider.generate(request, persona)
        except TimeoutError:
            return await self._remember_failure(request, ErrorCode.PROVIDER_TIMEOUT, retryable=True)
        except ProviderRateLimitError:
            return await self._remember_failure(request, ErrorCode.RATE_LIMITED, retryable=True)
        except ProviderInvalidOutputError:
            return await self._remember_failure(request, ErrorCode.PROVIDER_INVALID_OUTPUT)
        except ProviderError as exc:
            return await self._remember_failure(
                request, ErrorCode.PROVIDER_UNAVAILABLE, retryable=exc.retryable
            )

        if not text or len(text.encode("utf-8")) > request.limits.max_utf8_bytes:
            return await self._remember_failure(request, ErrorCode.PROVIDER_INVALID_OUTPUT)

        response = DialogueResponse(
            request_id=request.request_id,
            status="completed",
            candidate=DialogueCandidate(text=text, language=request.event.language),
            persona=PersonaReference(id=persona.id, revision=persona.revision),
            memory=MemorySummary(),
        )
        async with self._lock:
            self._responses[key] = response
        return response

    async def record_outcome(self, outcome: OutcomeRequest) -> None:
        async with self._lock:
            self._outcomes[(outcome.server_id, outcome.request_id)] = outcome

    async def _remember_failure(
        self, request: DialogueRequest, code: ErrorCode, retryable: bool = False
    ) -> DialogueResponse:
        response = DialogueResponse(
            request_id=request.request_id,
            status="failed",
            error=DialogueError(code=code, retryable=retryable),
        )
        async with self._lock:
            self._responses[(request.server_id, request.request_id)] = response
        return response

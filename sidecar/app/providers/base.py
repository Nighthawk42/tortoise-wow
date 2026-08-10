from __future__ import annotations

from typing import Protocol

from app.models.api import DialogueRequest
from app.models.personas import ResolvedPersona


class DialogueProvider(Protocol):
    name: str

    async def generate(self, request: DialogueRequest, persona: ResolvedPersona) -> str: ...


class ProviderError(Exception):
    pass


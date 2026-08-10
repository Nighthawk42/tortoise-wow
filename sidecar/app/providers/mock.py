from __future__ import annotations

import hashlib

from app.models.api import DialogueRequest
from app.models.personas import ResolvedPersona


class MockDialogueProvider:
    name = "mock"

    def __init__(self) -> None:
        self._requests = 0
        self._succeeded = 0

    async def generate(self, request: DialogueRequest, persona: ResolvedPersona) -> str:
        self._requests += 1
        text = request.event.text.casefold()
        if "sentinel hill" in text:
            response = "yeah, follow the road southeast from here. omw that way too"
        else:
            if any(word in text for word in ("hello", "hey", "hi ")):
                choices = ("hey, how's it going?", "hey!", "hi, just wrapping something up")
            else:
                choices = (
                    "not completely sure, but i can check",
                    "yeah, give me a sec",
                    "i think so, what part are you on?",
                )
            digest = hashlib.sha256(f"{request.request_id}:{persona.revision}".encode()).digest()
            response = choices[digest[0] % len(choices)]
        self._succeeded += 1
        return response

    async def aclose(self) -> None:
        return None

    def metrics_snapshot(self) -> dict[str, int | float]:
        return {
            "requests": self._requests,
            "succeeded": self._succeeded,
            "timed_out": 0,
            "rate_limited": 0,
            "invalid_responses": 0,
            "unavailable": 0,
            "cancelled": 0,
            "in_flight": 0,
            "peak_in_flight": 0,
            "average_latency_ms": 0.0,
        }

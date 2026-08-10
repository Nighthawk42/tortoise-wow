from __future__ import annotations

import hashlib

from app.models.api import DialogueRequest
from app.models.personas import ResolvedPersona


class MockDialogueProvider:
    name = "mock"

    async def generate(self, request: DialogueRequest, persona: ResolvedPersona) -> str:
        text = request.event.text.casefold()
        if "sentinel hill" in text:
            return "yeah, follow the road southeast from here. omw that way too"
        if any(word in text for word in ("hello", "hey", "hi ")):
            choices = ("hey, how's it going?", "hey!", "hi, just wrapping something up")
        else:
            choices = (
                "not completely sure, but i can check",
                "yeah, give me a sec",
                "i think so, what part are you on?",
            )
        digest = hashlib.sha256(f"{request.request_id}:{persona.revision}".encode()).digest()
        return choices[digest[0] % len(choices)]


from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.models.api import DialogueRequest
from app.personas.registry import PersonaRegistry
from app.providers.factory import create_provider
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    settings = Settings.from_environment()
    if settings.provider == "mock":
        raise SystemExit("set TORTOISE_SIDECAR_PROVIDER to openrouter or openai-compatible")
    request_data = json.loads(
        (ROOT / "tests/fixtures/dialogue-request.json").read_text(encoding="utf-8")
    )
    request_data["request_id"] = "793e6458-8918-4184-bb87-122fdc8f4eed"
    request_data["deadline"] = (datetime.now(UTC) + timedelta(seconds=60)).isoformat()
    request_data["event"]["occurred_at"] = datetime.now(UTC).isoformat()
    request = DialogueRequest.model_validate(request_data)
    registry = PersonaRegistry.load(settings.config_dir, settings.server_id)
    provider = create_provider(settings)
    try:
        persona = registry.resolve(request)
        response = await provider.generate(request, persona)
        print(f"provider={provider.name} profile={persona.model_profile}")
        print(f"response={response}")
        print(f"metrics={provider.metrics_snapshot()}")
    finally:
        await provider.aclose()


if __name__ == "__main__":
    asyncio.run(main())

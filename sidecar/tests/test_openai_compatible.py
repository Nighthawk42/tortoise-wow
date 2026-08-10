from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from app.models.api import DialogueRequest
from app.models.providers import ModelRoute, ProviderRoutes
from app.personas.registry import PersonaRegistry
from app.providers.base import ProviderInvalidOutputError, ProviderRateLimitError
from app.providers.openai_compatible import OpenAICompatibleDialogueProvider

ROOT = Path(__file__).resolve().parents[1]


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeClient:
    def __init__(
        self,
        response: FakeResponse | None = None,
        *,
        delay: float = 0,
        gate: asyncio.Event | None = None,
    ) -> None:
        self.response = response or FakeResponse(
            {"choices": [{"message": {"content": "  hey there!\n"}}]}
        )
        self.delay = delay
        self.gate = gate
        self.calls: list[dict[str, Any]] = []
        self.concurrent = 0
        self.peak_concurrent = 0

    async def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        self.concurrent += 1
        self.peak_concurrent = max(self.peak_concurrent, self.concurrent)
        try:
            if self.gate is not None:
                self.gate.set()
                await asyncio.Event().wait()
            if self.delay:
                await asyncio.sleep(self.delay)
            return self.response
        finally:
            self.concurrent -= 1

    async def aclose(self) -> None:
        return None


def _request_and_persona(
    dialogue_request: dict[str, object],
) -> tuple[DialogueRequest, Any]:
    request = DialogueRequest.model_validate(dialogue_request).model_copy(
        update={"deadline": datetime.now(UTC) + timedelta(seconds=10)}
    )
    persona = PersonaRegistry.load(ROOT / "config", "turtle-dev").resolve(request)
    return request, persona


def _provider(client: FakeClient, **overrides: Any) -> OpenAICompatibleDialogueProvider:
    values = {
        "name": "test-openai-compatible",
        "api_base": "https://provider.example/v1",
        "api_key": "test-key",
        "model_override": None,
        "routes": ProviderRoutes(
            schema_version=1,
            profiles={"dialogue-small": ModelRoute(model="example/free", max_completion_tokens=72)},
        ),
        "timeout_seconds": 1.0,
        "max_concurrency": 2,
        "requests_per_minute": 100,
        "client": client,
    }
    values.update(overrides)
    return OpenAICompatibleDialogueProvider(**values)


def test_provider_sends_compiled_openai_request(
    dialogue_request: dict[str, object],
) -> None:
    async def scenario() -> None:
        request, persona = _request_and_persona(dialogue_request)
        client = FakeClient()
        provider = _provider(client)

        assert await provider.generate(request, persona) == "hey there!"
        call = client.calls[0]
        assert call["url"] == "https://provider.example/v1/chat/completions"
        assert call["headers"]["Authorization"] == "Bearer test-key"
        assert call["json"]["model"] == "example/free"
        assert call["json"]["max_tokens"] == 72
        assert call["json"]["temperature"] == persona.temperature
        assert call["json"]["stream"] is False
        assert [message["role"] for message in call["json"]["messages"]] == [
            "system",
            "user",
        ]
        assert provider.metrics_snapshot()["succeeded"] == 1

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{"message": {"content": None}}]},
        {"choices": [{"message": {"content": "  \n"}}]},
        ValueError("not JSON"),
    ],
)
def test_provider_rejects_malformed_output(
    dialogue_request: dict[str, object], payload: Any
) -> None:
    async def scenario() -> None:
        request, persona = _request_and_persona(dialogue_request)
        provider = _provider(FakeClient(FakeResponse(payload)))
        with pytest.raises(ProviderInvalidOutputError):
            await provider.generate(request, persona)
        assert provider.metrics_snapshot()["invalid_responses"] == 1

    asyncio.run(scenario())


def test_provider_enforces_timeout(dialogue_request: dict[str, object]) -> None:
    async def scenario() -> None:
        request, persona = _request_and_persona(dialogue_request)
        provider = _provider(FakeClient(delay=0.1), timeout_seconds=0.01)
        with pytest.raises(TimeoutError):
            await provider.generate(request, persona)
        assert provider.metrics_snapshot()["timed_out"] == 1
        assert provider.metrics_snapshot()["in_flight"] == 0

    asyncio.run(scenario())


def test_provider_propagates_cancellation(dialogue_request: dict[str, object]) -> None:
    async def scenario() -> None:
        request, persona = _request_and_persona(dialogue_request)
        entered = asyncio.Event()
        provider = _provider(FakeClient(gate=entered))
        task = asyncio.create_task(provider.generate(request, persona))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert provider.metrics_snapshot()["cancelled"] == 1
        assert provider.metrics_snapshot()["in_flight"] == 0

    asyncio.run(scenario())


def test_provider_rejects_above_local_rate_limit(
    dialogue_request: dict[str, object],
) -> None:
    async def scenario() -> None:
        request, persona = _request_and_persona(dialogue_request)
        provider = _provider(FakeClient(), requests_per_minute=1)
        await provider.generate(request, persona)
        with pytest.raises(ProviderRateLimitError):
            await provider.generate(request, persona)
        metrics = provider.metrics_snapshot()
        assert metrics["requests"] == 2
        assert metrics["rate_limited"] == 1

    asyncio.run(scenario())


def test_provider_bounds_parallel_load(dialogue_request: dict[str, object]) -> None:
    async def scenario() -> None:
        request, persona = _request_and_persona(dialogue_request)
        client = FakeClient(delay=0.01)
        provider = _provider(client, max_concurrency=3)
        results = await asyncio.gather(*(provider.generate(request, persona) for _ in range(24)))
        assert results == ["hey there!"] * 24
        assert client.peak_concurrent == 3
        metrics = provider.metrics_snapshot()
        assert metrics["succeeded"] == 24
        assert metrics["peak_in_flight"] == 3

    asyncio.run(scenario())

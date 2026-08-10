from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any, Protocol
from urllib.parse import urlsplit

import httpx2

from app.models.api import DialogueRequest
from app.models.personas import ResolvedPersona
from app.models.providers import ProviderRoutes
from app.prompts import DialoguePromptCompiler
from app.providers.base import (
    ProviderConfigurationError,
    ProviderError,
    ProviderInvalidOutputError,
    ProviderRateLimitError,
)


class HttpClient(Protocol):
    async def post(self, url: str, **kwargs: Any) -> Any: ...

    async def aclose(self) -> None: ...


class SlidingWindowRateLimiter:
    def __init__(self, requests: int, window_seconds: float = 60.0) -> None:
        if requests < 1 or window_seconds <= 0:
            raise ProviderConfigurationError("rate limit values must be positive")
        self._limit = requests
        self._window = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def admit(self) -> None:
        now = time.monotonic()
        async with self._lock:
            cutoff = now - self._window
            while self._timestamps and self._timestamps[0] <= cutoff:
                self._timestamps.popleft()
            if len(self._timestamps) >= self._limit:
                raise ProviderRateLimitError("provider request rate limit reached")
            self._timestamps.append(now)


class ProviderMetrics:
    def __init__(self) -> None:
        self.requests = 0
        self.succeeded = 0
        self.timed_out = 0
        self.rate_limited = 0
        self.invalid_responses = 0
        self.unavailable = 0
        self.cancelled = 0
        self.in_flight = 0
        self.peak_in_flight = 0
        self._total_latency_ms = 0.0

    def begin(self) -> float:
        self.requests += 1
        return time.monotonic()

    def enter_provider(self) -> None:
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)

    def leave_provider(self) -> None:
        self.in_flight -= 1

    def finish(self, started: float) -> None:
        self._total_latency_ms += (time.monotonic() - started) * 1000

    def snapshot(self) -> dict[str, int | float]:
        average = self._total_latency_ms / self.requests if self.requests else 0.0
        return {
            "requests": self.requests,
            "succeeded": self.succeeded,
            "timed_out": self.timed_out,
            "rate_limited": self.rate_limited,
            "invalid_responses": self.invalid_responses,
            "unavailable": self.unavailable,
            "cancelled": self.cancelled,
            "in_flight": self.in_flight,
            "peak_in_flight": self.peak_in_flight,
            "average_latency_ms": round(average, 3),
        }


class OpenAICompatibleDialogueProvider:
    def __init__(
        self,
        *,
        name: str,
        api_base: str,
        api_key: str | None,
        routes: ProviderRoutes,
        model_override: str | None,
        timeout_seconds: float,
        max_concurrency: int,
        requests_per_minute: int,
        http_referer: str | None = None,
        app_title: str | None = None,
        client: HttpClient | None = None,
        compiler: DialoguePromptCompiler | None = None,
    ) -> None:
        parsed = urlsplit(api_base)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ProviderConfigurationError("provider API base must be an HTTP(S) URL")
        if timeout_seconds <= 0 or max_concurrency < 1:
            raise ProviderConfigurationError("provider timeout and concurrency must be positive")

        self.name = name
        self._completion_url = f"{api_base.rstrip('/')}/chat/completions"
        self._routes = routes
        self._model_override = model_override
        self._timeout_seconds = timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._rate_limiter = SlidingWindowRateLimiter(requests_per_minute)
        self._compiler = compiler or DialoguePromptCompiler()
        self._client = client or httpx2.AsyncClient(follow_redirects=False)
        self._owns_client = client is None
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"
        if http_referer:
            self._headers["HTTP-Referer"] = http_referer
        if app_title:
            self._headers["X-Title"] = app_title
        self._metrics = ProviderMetrics()

    async def generate(self, request: DialogueRequest, persona: ResolvedPersona) -> str:
        started = self._metrics.begin()
        entered_provider = False
        try:
            await self._rate_limiter.admit()
            route = self._routes.route(persona.model_profile)
            prompt = self._compiler.compile(request, persona)
            remaining = (request.deadline - datetime.now(UTC)).total_seconds()
            timeout_seconds = min(self._timeout_seconds, remaining)
            if timeout_seconds <= 0:
                raise TimeoutError("dialogue deadline expired")

            async with self._semaphore:
                self._metrics.enter_provider()
                entered_provider = True
                try:
                    async with asyncio.timeout(timeout_seconds):
                        response = await self._client.post(
                            self._completion_url,
                            headers=self._headers,
                            json={
                                "model": self._model_override or route.model,
                                "messages": prompt.as_api_messages(),
                                "temperature": persona.temperature,
                                "max_tokens": route.max_completion_tokens,
                                "stream": False,
                            },
                            timeout=timeout_seconds,
                        )
                finally:
                    self._metrics.leave_provider()
                    entered_provider = False

            if response.status_code == 429:
                raise ProviderRateLimitError("upstream provider rate limited the request")
            if response.status_code >= 400:
                error = ProviderError(f"upstream provider returned HTTP {response.status_code}")
                error.retryable = response.status_code in {408, 409} or response.status_code >= 500
                raise error
            text = self._extract_text(response)
            self._metrics.succeeded += 1
            return text
        except ProviderRateLimitError:
            self._metrics.rate_limited += 1
            raise
        except ProviderInvalidOutputError:
            self._metrics.invalid_responses += 1
            raise
        except (TimeoutError, httpx2.TimeoutException) as exc:
            self._metrics.timed_out += 1
            raise TimeoutError("provider request timed out") from exc
        except asyncio.CancelledError:
            self._metrics.cancelled += 1
            raise
        except httpx2.RequestError as exc:
            self._metrics.unavailable += 1
            raise ProviderError("provider transport unavailable") from exc
        except ProviderError:
            self._metrics.unavailable += 1
            raise
        except ValueError as exc:
            self._metrics.invalid_responses += 1
            raise ProviderInvalidOutputError("provider response was not valid JSON") from exc
        finally:
            if entered_provider:
                self._metrics.leave_provider()
            self._metrics.finish(started)

    @staticmethod
    def _extract_text(response: Any) -> str:
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as exc:
            raise ProviderInvalidOutputError("provider response has no chat content") from exc
        if not isinstance(content, str):
            raise ProviderInvalidOutputError("provider chat content must be text")
        if "\x00" in content:
            raise ProviderInvalidOutputError("provider chat content contains a null byte")
        text = " ".join(content.split())
        if not text:
            raise ProviderInvalidOutputError("provider chat content is empty")
        return text

    def metrics_snapshot(self) -> dict[str, int | float]:
        return self._metrics.snapshot()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

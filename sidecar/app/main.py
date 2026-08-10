from __future__ import annotations

import secrets
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.models.api import (
    DialogueRequest,
    DialogueResponse,
    ErrorCode,
    HealthStatus,
    OutcomeAccepted,
    OutcomeRequest,
)
from app.personas.registry import PersonaRegistry, RegistryError
from app.providers.mock import MockDialogueProvider
from app.service import DialogueService
from app.settings import Settings


class RuntimeState:
    def __init__(self) -> None:
        self.service: DialogueService | None = None
        self.registry_error: str | None = None


def _authorization_dependency(settings: Settings) -> Callable[..., None]:
    def authorize(authorization: Annotated[str | None, Header()] = None) -> None:
        if settings.service_token is None:
            return
        scheme, _, value = (authorization or "").partition(" ")
        if scheme.casefold() != "bearer" or not secrets.compare_digest(
            value, settings.service_token
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")

    return authorize


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_environment()
    runtime = RuntimeState()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            if resolved_settings.provider != "mock":
                raise RegistryError(
                    code=ErrorCode.PERSONA_INVALID,
                    message=f"unsupported provider {resolved_settings.provider}",
                )
            registry = PersonaRegistry.load(
                resolved_settings.config_dir, resolved_settings.server_id
            )
            runtime.service = DialogueService(registry, MockDialogueProvider())
        except RegistryError as exc:
            runtime.registry_error = str(exc)
        yield

    app = FastAPI(
        title="Tortoise AI Sidecar",
        version="0.1.0",
        lifespan=lifespan,
    )
    authorize = _authorization_dependency(resolved_settings)

    @app.get("/health/live", response_model=HealthStatus, response_model_exclude_none=True)
    async def live() -> HealthStatus:
        return HealthStatus(status="live", provider=resolved_settings.provider)

    @app.get("/health/ready", response_model=HealthStatus, response_model_exclude_none=True)
    async def ready() -> HealthStatus:
        if runtime.service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready", "reason": runtime.registry_error},
            )
        registry = runtime.service.registry
        return HealthStatus(
            status="ready",
            provider=resolved_settings.provider,
            registry_revision=registry.revision,
            profiles=registry.profile_count,
            bindings=registry.binding_count,
        )

    @app.post(
        "/v1/dialogue",
        response_model=DialogueResponse,
        dependencies=[Depends(authorize)],
    )
    async def dialogue(request: DialogueRequest) -> DialogueResponse:
        if runtime.service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        return await runtime.service.dialogue(request)

    @app.post(
        "/v1/outcomes",
        response_model=OutcomeAccepted,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(authorize)],
    )
    async def outcomes(request: OutcomeRequest) -> OutcomeAccepted:
        if runtime.service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        if request.server_id != resolved_settings.server_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        await runtime.service.record_outcome(request)
        return OutcomeAccepted(request_id=request.request_id)

    return app


app = create_app()

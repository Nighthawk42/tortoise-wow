from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ShortText = Annotated[str, Field(min_length=1, max_length=255)]
ActorId = Annotated[str, Field(min_length=3, max_length=160, pattern=r"^[A-Za-z0-9:._-]+$")]


class DialogueChannel(StrEnum):
    WHISPER = "whisper"
    SAY = "say"
    PARTY = "party"
    GUILD = "guild"


class DialogueEvent(StrictModel):
    type: Literal["dialogue.requested"]
    occurred_at: datetime
    channel: DialogueChannel
    text: Annotated[str, Field(min_length=1, max_length=1024)]
    language: ShortText


class BotSnapshot(StrictModel):
    actor_id: ActorId
    persona_id: Annotated[str, Field(min_length=3, max_length=160)] | None = None
    character_guid_low: int | None = Field(default=None, ge=1)
    name: ShortText
    level: int = Field(ge=1, le=255)
    race: ShortText
    class_name: ShortText = Field(alias="class")
    zone: ShortText
    subzone: str = Field(default="", max_length=255)
    group_role: str | None = Field(default=None, max_length=40)


class SpeakerSnapshot(StrictModel):
    actor_id: ActorId
    display_name: ShortText
    kind: Literal["player", "playerbot"]
    relationship: Annotated[str, Field(min_length=1, max_length=40)]


class DialogueLimits(StrictModel):
    max_utf8_bytes: int = Field(default=255, ge=1, le=255)
    allowed_output: list[Literal["chat.text"]] = Field(min_length=1, max_length=1)


class DialogueContext(StrictModel):
    recent_dialogue: list[Annotated[str, Field(max_length=1024)]] = Field(
        default_factory=list, max_length=12
    )
    facts: list[Annotated[str, Field(max_length=512)]] = Field(default_factory=list, max_length=20)


class DialogueRequest(StrictModel):
    contract_version: Literal["1.0"]
    request_id: UUID
    server_id: ShortText
    realm_id: int = Field(ge=1)
    deadline: datetime
    event: DialogueEvent
    bot: BotSnapshot
    speaker: SpeakerSnapshot
    limits: DialogueLimits
    context: DialogueContext = Field(default_factory=DialogueContext)

    @model_validator(mode="after")
    def require_timezone_aware_timestamps(self) -> DialogueRequest:
        for value, field_name in (
            (self.deadline, "deadline"),
            (self.event.occurred_at, "event.occurred_at"),
        ):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{field_name} must include a timezone")
        return self


class DialogueCandidate(StrictModel):
    type: Literal["chat.text"] = "chat.text"
    text: ShortText
    language: ShortText


class PersonaReference(StrictModel):
    id: str
    revision: str


class MemorySummary(StrictModel):
    retrieval_count: int = Field(default=0, ge=0)
    write_proposals: int = Field(default=0, ge=0)


class ErrorCode(StrEnum):
    INVALID_REQUEST = "invalid_request"
    DEADLINE_EXPIRED = "deadline_expired"
    PERSONA_NOT_FOUND = "persona_not_found"
    PERSONA_INVALID = "persona_invalid"
    POLICY_DENIED = "policy_denied"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_INVALID_OUTPUT = "provider_invalid_output"
    MEMORY_UNAVAILABLE = "memory_unavailable"
    INTERNAL_ERROR = "internal_error"


class DialogueError(StrictModel):
    code: ErrorCode
    retryable: bool = False


class DialogueResponse(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    request_id: UUID
    status: Literal["completed", "failed"]
    candidate: DialogueCandidate | None = None
    persona: PersonaReference | None = None
    memory: MemorySummary | None = None
    error: DialogueError | None = None

    @model_validator(mode="after")
    def validate_status_shape(self) -> DialogueResponse:
        if self.status == "completed" and (self.candidate is None or self.persona is None):
            raise ValueError("completed responses require candidate and persona")
        if self.status == "failed" and self.error is None:
            raise ValueError("failed responses require an error")
        return self


class OutcomeValue(StrEnum):
    EMITTED = "emitted"
    EXPIRED = "expired"
    CONTEXT_CHANGED = "context_changed"
    POLICY_REJECTED = "policy_rejected"
    BOT_UNAVAILABLE = "bot_unavailable"


class OutcomeRequest(StrictModel):
    contract_version: Literal["1.0"]
    request_id: UUID
    server_id: ShortText
    occurred_at: datetime
    outcome: OutcomeValue
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_timezone_aware_timestamp(self) -> OutcomeRequest:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return self


class OutcomeAccepted(StrictModel):
    contract_version: Literal["1.0"] = "1.0"
    request_id: UUID
    status: Literal["accepted"] = "accepted"


class ProviderMetricsSnapshot(StrictModel):
    requests: int = Field(ge=0)
    succeeded: int = Field(ge=0)
    timed_out: int = Field(ge=0)
    rate_limited: int = Field(ge=0)
    invalid_responses: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    cancelled: int = Field(ge=0)
    in_flight: int = Field(ge=0)
    peak_in_flight: int = Field(ge=0)
    average_latency_ms: float = Field(ge=0.0)


class HealthStatus(StrictModel):
    status: Literal["live", "ready", "not_ready"]
    provider: str | None = None
    registry_revision: str | None = None
    profiles: int | None = None
    bindings: int | None = None
    metrics: ProviderMetricsSnapshot | None = None

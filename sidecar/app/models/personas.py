from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


UnitFloat = Annotated[float, Field(ge=0.0, le=1.0)]
ProfileId = Annotated[str, Field(min_length=3, max_length=160, pattern=r"^[a-z0-9._-]+$")]
SafeString = Annotated[str, Field(min_length=1, max_length=255)]


class ModelSelection(StrictModel):
    profile: ProfileId
    temperature: float = Field(ge=0.0, le=2.0)


class Identity(StrictModel):
    handle: SafeString
    presentation: SafeString
    player_since: SafeString
    real_world_details: Literal["never_invent"]


class Roles(StrictModel):
    preferred: list[SafeString] = Field(default_factory=list, max_length=5)
    willing: list[SafeString] = Field(default_factory=list, max_length=5)


class Mistakes(StrictModel):
    misses_mechanics_chance: UnitFloat
    asks_when_uncertain: bool
    admits_not_knowing: bool


class Gameplay(StrictModel):
    experience: UnitFloat
    mechanical_skill: UnitFloat
    game_knowledge: UnitFloat
    confidence: UnitFloat
    risk_tolerance: UnitFloat
    patience: UnitFloat
    efficiency_vs_exploration: UnitFloat
    preferred_content: list[SafeString] = Field(min_length=1, max_length=10)
    avoids: list[SafeString] = Field(default_factory=list, max_length=10)
    roles: Roles
    mistakes: Mistakes


class SessionMinutes(StrictModel):
    min: int = Field(ge=5, le=1440)
    max: int = Field(ge=5, le=1440)

    @model_validator(mode="after")
    def ordered(self) -> SessionMinutes:
        if self.min > self.max:
            raise ValueError("session minimum cannot exceed maximum")
        return self


class Activity(StrictModel):
    style: SafeString
    typical_session_minutes: SessionMinutes
    break_frequency: SafeString
    afk_style: SafeString
    repeat_content_tolerance: UnitFloat


class Goals(StrictModel):
    current: list[SafeString] = Field(default_factory=list, max_length=10)
    long_term: list[SafeString] = Field(default_factory=list, max_length=10)
    persistence: UnitFloat
    changes_mind_chance: UnitFloat


class Abbreviations(StrictModel):
    frequency: SafeString
    examples: list[Annotated[str, Field(min_length=1, max_length=20)]] = Field(
        default_factory=list, max_length=12
    )


class ResponseCadence(StrictModel):
    minimum_delay_ms: int = Field(ge=0, le=60_000)
    reading_ms_per_character: int = Field(ge=0, le=1_000)
    sometimes_does_not_reply: bool


class Communication(StrictModel):
    register_name: SafeString = Field(alias="register")
    message_length: SafeString
    capitalization: SafeString
    punctuation: SafeString
    typo_rate: UnitFloat
    correction_rate: UnitFloat
    abbreviations: Abbreviations
    emotes: SafeString
    humor: SafeString
    response_cadence: ResponseCadence
    avoids: list[SafeString] = Field(default_factory=list, max_length=15)


class Channels(StrictModel):
    whisper: bool = True
    say: bool = True
    party: bool = True
    guild: bool = True
    world: bool = False


class Social(StrictModel):
    sociability: UnitFloat
    helpfulness: UnitFloat
    group_initiative: UnitFloat
    leadership: UnitFloat
    competitiveness: UnitFloat
    stranger_trust: UnitFloat
    conflict_style: SafeString
    loot_attitude: SafeString
    group_exit_style: SafeString
    channels: Channels


class Knowledge(StrictModel):
    game_era: SafeString
    perspective: SafeString
    knows_game_terms: bool
    discusses_mechanics: SafeString
    allows_uncertainty: bool
    spoiler_behavior: SafeString
    forbidden: list[SafeString] = Field(default_factory=list, max_length=15)


class MemoryPolicy(StrictModel):
    profile: ProfileId
    share_across_bound_alts: bool
    remember_player_names: bool
    remember_shared_runs: bool
    remember_favors_and_promises: bool
    remember_private_chat_content: bool
    relationship_scope: SafeString
    episodic_ttl_days: int = Field(ge=0, le=3650)


class Safety(StrictModel):
    never_invent_real_world_identity: Literal[True]
    never_claim_offline_contact: Literal[True]
    refuse_personal_data_requests: Literal[True]
    refuse_admin_impersonation: Literal[True]
    never_claim_unobserved_gameplay: Literal[True]


class Provenance(StrictModel):
    type: Literal["handcrafted"]
    authored_by: SafeString


class PlayerProfile(StrictModel):
    schema_version: Literal[1]
    kind: Literal["player_profile"]
    id: ProfileId
    provenance: Provenance
    identity: Identity
    gameplay: Gameplay
    activity: Activity
    goals: Goals
    communication: Communication
    social: Social
    knowledge: Knowledge
    model: ModelSelection
    memory: MemoryPolicy
    safety: Safety


class NumericRange(StrictModel):
    min: float = Field(ge=0.0, le=2.0)
    max: float = Field(ge=0.0, le=2.0)

    @model_validator(mode="after")
    def ordered(self) -> NumericRange:
        if self.min > self.max:
            raise ValueError("range minimum cannot exceed maximum")
        return self


class WeightedChoice(StrictModel):
    value: SafeString
    weight: int = Field(gt=0, le=1000)


class ArchetypeSelection(StrictModel):
    race: SafeString
    class_name: SafeString = Field(alias="class")


class ArchetypeModel(StrictModel):
    profile: ProfileId
    temperature: NumericRange


class ArchetypeGeneration(StrictModel):
    profile_id_prefix: ProfileId
    stable_seed_required: Literal[True]
    traits: dict[ProfileId, NumericRange] = Field(min_length=1, max_length=30)
    weighted_preferences: list[WeightedChoice] = Field(min_length=1, max_length=20)
    communication_styles: list[WeightedChoice] = Field(min_length=1, max_length=20)
    model: ArchetypeModel


class PlayerArchetype(StrictModel):
    schema_version: Literal[1]
    kind: Literal["player_archetype"]
    id: ProfileId
    selection: ArchetypeSelection
    generation: ArchetypeGeneration


class CharacterOverlay(StrictModel):
    status: SafeString
    current_role: SafeString
    seriousness: UnitFloat


class RosterBinding(StrictModel):
    character_guid_low: int = Field(ge=1)
    expected_character_name: SafeString
    persona_id: ProfileId | None = None
    archetype_id: ProfileId | None = None
    stable_seed: int | None = Field(default=None, ge=0)
    enabled: bool = True
    character_overlay: CharacterOverlay

    @model_validator(mode="after")
    def validate_source(self) -> RosterBinding:
        if (self.persona_id is None) == (self.archetype_id is None):
            raise ValueError("binding requires exactly one persona_id or archetype_id")
        if self.archetype_id is not None and self.stable_seed is None:
            raise ValueError("archetype bindings require a stable_seed")
        if self.persona_id is not None and self.stable_seed is not None:
            raise ValueError("handcrafted bindings cannot set stable_seed")
        return self


class Roster(StrictModel):
    schema_version: Literal[1]
    server_id: SafeString
    realm_id: int = Field(ge=1)
    bindings: list[RosterBinding] = Field(min_length=1)


class ResolvedPersona(StrictModel):
    id: ProfileId
    revision: str
    source_kind: Literal["handcrafted", "system_archetype"]
    model_profile: ProfileId
    temperature: float = Field(ge=0.0, le=2.0)
    prompt_summary: Annotated[str, Field(min_length=1, max_length=2000)]
    communication_style: SafeString
    traits: dict[str, float] = Field(default_factory=dict)

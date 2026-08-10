from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from app.models.api import BotSnapshot, DialogueRequest, ErrorCode
from app.models.personas import (
    PlayerArchetype,
    PlayerProfile,
    ResolvedPersona,
    Roster,
    RosterBinding,
    WeightedChoice,
)


class RegistryError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _load_yaml[ModelT: BaseModel](path: Path, model: type[ModelT]) -> ModelT:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return model.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise RegistryError(ErrorCode.PERSONA_INVALID, f"invalid {path.name}: {exc}") from exc


def _digest(value: Any) -> str:
    def normalize(item: Any) -> Any:
        if isinstance(item, BaseModel):
            return item.model_dump(mode="json", by_alias=True)
        if isinstance(item, dict):
            return {key: normalize(nested) for key, nested in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(nested) for nested in item]
        return item

    encoded = json.dumps(normalize(value), sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _unit(seed: int, namespace: str) -> float:
    digest = hashlib.sha256(f"{seed}:{namespace}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / ((1 << 64) - 1)


def _choose(seed: int, namespace: str, choices: list[WeightedChoice]) -> str:
    total = sum(choice.weight for choice in choices)
    target = _unit(seed, namespace) * total
    cumulative = 0
    for choice in choices:
        cumulative += choice.weight
        if target < cumulative:
            return choice.value
    return choices[-1].value


class PersonaRegistry:
    def __init__(
        self,
        profiles: dict[str, PlayerProfile],
        archetypes: dict[str, PlayerArchetype],
        roster: Roster,
    ) -> None:
        self.profiles = profiles
        self.archetypes = archetypes
        self.roster = roster
        self._bindings: dict[int, RosterBinding] = {}
        for binding in roster.bindings:
            if binding.character_guid_low in self._bindings:
                raise RegistryError(
                    ErrorCode.PERSONA_INVALID,
                    f"duplicate binding for character {binding.character_guid_low}",
                )
            self._bindings[binding.character_guid_low] = binding
        self.revision = _digest(
            {
                "profiles": profiles,
                "archetypes": archetypes,
                "roster": roster,
            }
        )

    @classmethod
    def load(cls, config_dir: Path, expected_server_id: str) -> PersonaRegistry:
        profiles: dict[str, PlayerProfile] = {}
        for path in sorted((config_dir / "personas").glob("*.yaml")):
            profile = _load_yaml(path, PlayerProfile)
            if profile.id in profiles:
                raise RegistryError(ErrorCode.PERSONA_INVALID, f"duplicate profile {profile.id}")
            profiles[profile.id] = profile

        archetypes: dict[str, PlayerArchetype] = {}
        for path in sorted((config_dir / "archetypes").glob("*.yaml")):
            archetype = _load_yaml(path, PlayerArchetype)
            if archetype.id in archetypes:
                raise RegistryError(
                    ErrorCode.PERSONA_INVALID, f"duplicate archetype {archetype.id}"
                )
            archetypes[archetype.id] = archetype

        roster = _load_yaml(config_dir / "bindings.yaml", Roster)
        if roster.server_id != expected_server_id:
            raise RegistryError(
                ErrorCode.PERSONA_INVALID,
                f"roster server_id {roster.server_id!r} does not match {expected_server_id!r}",
            )
        for binding in roster.bindings:
            if binding.persona_id and binding.persona_id not in profiles:
                raise RegistryError(
                    ErrorCode.PERSONA_INVALID, f"unknown profile {binding.persona_id}"
                )
            if binding.archetype_id and binding.archetype_id not in archetypes:
                raise RegistryError(
                    ErrorCode.PERSONA_INVALID, f"unknown archetype {binding.archetype_id}"
                )
        if not profiles and not archetypes:
            raise RegistryError(ErrorCode.PERSONA_INVALID, "persona registry is empty")
        return cls(profiles, archetypes, roster)

    @property
    def binding_count(self) -> int:
        return len(self._bindings)

    @property
    def profile_count(self) -> int:
        return len(self.profiles) + len(self.archetypes)

    def resolve(self, request: DialogueRequest) -> ResolvedPersona:
        if request.server_id != self.roster.server_id or request.realm_id != self.roster.realm_id:
            raise RegistryError(ErrorCode.POLICY_DENIED, "request is for another server or realm")
        guid = request.bot.character_guid_low or self._guid_from_actor_id(request.bot.actor_id)
        binding = self._bindings.get(guid)
        if binding is None or not binding.enabled:
            raise RegistryError(ErrorCode.PERSONA_NOT_FOUND, "no enabled roster binding")
        if binding.expected_character_name.casefold() != request.bot.name.casefold():
            raise RegistryError(ErrorCode.POLICY_DENIED, "bound character name does not match")
        if binding.persona_id:
            if request.bot.persona_id != binding.persona_id:
                raise RegistryError(
                    ErrorCode.POLICY_DENIED, "requested persona does not match binding"
                )
            return self._resolve_handcrafted(binding)
        return self._resolve_archetype(binding, request.bot)

    @staticmethod
    def _guid_from_actor_id(actor_id: str) -> int:
        try:
            return int(actor_id.rsplit(":", 1)[1])
        except (IndexError, ValueError) as exc:
            raise RegistryError(
                ErrorCode.INVALID_REQUEST, "actor_id has no character guid"
            ) from exc

    def _resolve_handcrafted(self, binding: RosterBinding) -> ResolvedPersona:
        assert binding.persona_id is not None
        profile = self.profiles[binding.persona_id]
        gameplay = profile.gameplay
        summary = (
            f"Simulate {profile.identity.handle}, a {profile.identity.presentation}. "
            f"They prefer {', '.join(gameplay.preferred_content[:3])}; current goals: "
            f"{'; '.join(profile.goals.current[:3])}. Write {profile.communication.message_length} "
            f"{profile.communication.register_name} messages with "
            f"{profile.communication.capitalization} capitalization and "
            f"{profile.communication.punctuation} punctuation. Admit uncertainty "
            "and never invent real-world identity, private information, or unobserved events."
        )
        return ResolvedPersona(
            id=profile.id,
            revision=_digest(profile),
            source_kind="handcrafted",
            model_profile=profile.model.profile,
            temperature=profile.model.temperature,
            prompt_summary=summary,
            communication_style=profile.communication.register_name,
            traits={
                "experience": gameplay.experience,
                "helpfulness": profile.social.helpfulness,
                "sociability": profile.social.sociability,
            },
        )

    def _resolve_archetype(
        self, binding: RosterBinding, bot: BotSnapshot
    ) -> ResolvedPersona:
        assert binding.archetype_id is not None and binding.stable_seed is not None
        archetype = self.archetypes[binding.archetype_id]
        if (
            archetype.selection.race.casefold() != bot.race.casefold()
            or archetype.selection.class_name.casefold() != bot.class_name.casefold()
        ):
            raise RegistryError(ErrorCode.POLICY_DENIED, "bot race/class does not match archetype")
        generated_id = f"{archetype.generation.profile_id_prefix}.{binding.character_guid_low}"
        if bot.persona_id != generated_id:
            raise RegistryError(
                ErrorCode.POLICY_DENIED, "generated persona id does not match binding"
            )

        traits = {
            name: bounds.min + _unit(binding.stable_seed, name) * (bounds.max - bounds.min)
            for name, bounds in archetype.generation.traits.items()
        }
        preference = _choose(
            binding.stable_seed, "preference", archetype.generation.weighted_preferences
        )
        style = _choose(
            binding.stable_seed, "communication", archetype.generation.communication_styles
        )
        temperature_range = archetype.generation.model.temperature
        temperature = temperature_range.min + _unit(
            binding.stable_seed, "temperature"
        ) * (temperature_range.max - temperature_range.min)
        materialized = {
            "id": generated_id,
            "source_revision": _digest(archetype),
            "stable_seed": binding.stable_seed,
            "traits": traits,
            "preference": preference,
            "style": style,
            "temperature": temperature,
        }
        return ResolvedPersona(
            id=generated_id,
            revision=_digest(materialized),
            source_kind="system_archetype",
            model_profile=archetype.generation.model.profile,
            temperature=temperature,
            prompt_summary=(
                f"Simulate a consistent player controlling this {bot.race} {bot.class_name}. "
                f"They favor {preference} and communicate in a {style} style. They may be "
                "uncertain and must never invent real-world identity, private data, or events."
            ),
            communication_style=style,
            traits=traits,
        )

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from app.models.api import DialogueRequest
from app.personas.registry import PersonaRegistry


def test_archetype_materialization_is_stable(dialogue_request: dict[str, object]) -> None:
    root = Path(__file__).resolve().parents[1]
    registry = PersonaRegistry.load(root / "config", "turtle-dev")
    request_data = deepcopy(dialogue_request)
    request_data["request_id"] = str(uuid4())
    request_data["bot"] = {
        "actor_id": "realm:1:character:9001",
        "persona_id": "generated.human.hunter.9001",
        "character_guid_low": 9001,
        "name": "Rowan",
        "level": 18,
        "race": "human",
        "class": "hunter",
        "zone": "Westfall",
        "subzone": "Sentinel Hill",
        "group_role": "damage",
    }
    request = DialogueRequest.model_validate(request_data)
    first = registry.resolve(request)
    second = registry.resolve(request)
    assert first == second
    assert first.source_kind == "system_archetype"
    assert first.id == "generated.human.hunter.9001"
    assert 0.60 <= first.temperature <= 0.88
    assert all(0.0 <= value <= 1.0 for value in first.traits.values())


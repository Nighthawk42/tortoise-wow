from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ModelRoute(StrictModel):
    model: Annotated[str, Field(min_length=1, max_length=255)]
    max_completion_tokens: int = Field(default=96, ge=1, le=512)


class ProviderRoutes(StrictModel):
    schema_version: Literal[1]
    profiles: dict[str, ModelRoute] = Field(min_length=1, max_length=50)

    @classmethod
    def load(cls, path: Path) -> ProviderRoutes:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            return cls.model_validate(raw)
        except (OSError, yaml.YAMLError, ValidationError) as exc:
            raise ValueError(f"invalid provider routes {path.name}: {exc}") from exc

    def route(self, profile: str) -> ModelRoute:
        try:
            return self.profiles[profile]
        except KeyError as exc:
            raise ValueError(f"no provider route for model profile {profile!r}") from exc

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def settings() -> Settings:
    return Settings(config_dir=ROOT / "config")


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def dialogue_request() -> dict[str, Any]:
    return json.loads((ROOT / "tests/fixtures/dialogue-request.json").read_text(encoding="utf-8"))


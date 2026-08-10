from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.settings import Settings


def test_settings_load_env_file_without_mutating_process_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "sidecar.env"
    config_dir = tmp_path / "config"
    env_file.write_text(
        "\n".join(
            (
                "TORTOISE_SIDECAR_PROVIDER=openrouter",
                "TORTOISE_LLM_API_KEY=file-test-key",
                "TORTOISE_LLM_MODEL=openrouter/free",
                f"TORTOISE_SIDECAR_CONFIG_DIR={config_dir.as_posix()}",
            )
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TORTOISE_SIDECAR_ENV_FILE", str(env_file))
    monkeypatch.delenv("TORTOISE_SIDECAR_PROVIDER", raising=False)
    monkeypatch.delenv("TORTOISE_LLM_API_KEY", raising=False)

    settings = Settings.from_environment()

    assert settings.provider == "openrouter"
    assert settings.provider_api_key == "file-test-key"
    assert settings.provider_model_override == "openrouter/free"
    assert settings.config_dir == config_dir
    assert "TORTOISE_LLM_API_KEY" not in os.environ


def test_process_environment_overrides_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "sidecar.env"
    env_file.write_text("TORTOISE_SIDECAR_PROVIDER=openrouter\n", encoding="utf-8")
    monkeypatch.setenv("TORTOISE_SIDECAR_ENV_FILE", str(env_file))
    monkeypatch.setenv("TORTOISE_SIDECAR_PROVIDER", "mock")

    assert Settings.from_environment().provider == "mock"

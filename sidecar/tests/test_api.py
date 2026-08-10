from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def test_health_reports_loaded_registry(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "live", "provider": "mock"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ready"
    assert body["profiles"] == 2
    assert body["bindings"] == 2
    assert body["registry_revision"].startswith("sha256:")
    assert body["metrics"]["requests"] == 0
    assert body["metrics"]["in_flight"] == 0


def test_handcrafted_dialogue_and_idempotency(
    client: TestClient, dialogue_request: dict[str, object]
) -> None:
    first = client.post("/v1/dialogue", json=dialogue_request)
    second = client.post("/v1/dialogue", json=dialogue_request)
    assert first.status_code == 200
    assert second.json() == first.json()
    body = first.json()
    assert body["status"] == "completed"
    assert body["candidate"]["type"] == "chat.text"
    assert len(body["candidate"]["text"].encode("utf-8")) <= 255
    assert body["persona"]["id"] == "players.mirae"
    assert body["persona"]["revision"].startswith("sha256:")
    metrics = client.get("/health/ready").json()["metrics"]
    assert metrics["requests"] == 1
    assert metrics["succeeded"] == 1


def test_expired_request_returns_typed_failure(
    client: TestClient, dialogue_request: dict[str, object]
) -> None:
    request = deepcopy(dialogue_request)
    request["request_id"] = str(uuid4())
    request["deadline"] = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    response = client.post("/v1/dialogue", json=request)
    assert response.json()["error"] == {"code": "deadline_expired", "retryable": False}


def test_binding_mismatch_is_rejected(
    client: TestClient, dialogue_request: dict[str, object]
) -> None:
    request = deepcopy(dialogue_request)
    request["request_id"] = str(uuid4())
    request["bot"]["name"] = "SomeoneElse"  # type: ignore[index]
    response = client.post("/v1/dialogue", json=request)
    assert response.json()["error"]["code"] == "policy_denied"


def test_outcome_is_accepted(client: TestClient, dialogue_request: dict[str, object]) -> None:
    client.post("/v1/dialogue", json=dialogue_request)
    outcome = {
        "contract_version": "1.0",
        "request_id": dialogue_request["request_id"],
        "server_id": "turtle-dev",
        "occurred_at": datetime.now(UTC).isoformat(),
        "outcome": "emitted",
        "reason": None,
    }
    response = client.post("/v1/outcomes", json=outcome)
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_service_token_protects_v1_routes(
    settings: Settings, dialogue_request: dict[str, object]
) -> None:
    secured_settings = replace(settings, service_token="test-service-token")
    with TestClient(create_app(secured_settings)) as secured_client:
        assert secured_client.post("/v1/dialogue", json=dialogue_request).status_code == 401
        response = secured_client.post(
            "/v1/dialogue",
            json=dialogue_request,
            headers={"Authorization": "Bearer test-service-token"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"


def test_openrouter_without_key_is_not_ready(settings: Settings) -> None:
    openrouter_settings = replace(settings, provider="openrouter", provider_api_key=None)
    with TestClient(create_app(openrouter_settings)) as openrouter_client:
        assert openrouter_client.get("/health/live").json() == {
            "status": "live",
            "provider": "openrouter",
        }
        response = openrouter_client.get("/health/ready")
        assert response.status_code == 503
        assert "API_KEY" in response.json()["detail"]["reason"]


def test_generic_provider_without_api_base_is_not_ready(settings: Settings) -> None:
    provider_settings = replace(
        settings,
        provider="openai-compatible",
        provider_api_base=None,
    )
    with TestClient(create_app(provider_settings)) as provider_client:
        response = provider_client.get("/health/ready")
        assert response.status_code == 503
        assert "API_BASE" in response.json()["detail"]["reason"]

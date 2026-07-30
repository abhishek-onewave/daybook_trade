from unittest.mock import patch

from backend.app.config import Settings
from backend.app.main import app
from fastapi.testclient import TestClient


def test_health_reports_database_and_config_booleans() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "live"
    assert payload["database"]["configured"] is True
    assert payload["database"]["connected"] is True
    assert payload["database"]["persistent"] is False
    assert isinstance(payload["integrations"]["anthropic_configured"], bool)
    assert isinstance(payload["integrations"]["alpaca_configured"], bool)
    assert isinstance(payload["integrations"]["tastytrade_configured"], bool)
    assert isinstance(payload["integrations"]["finnhub_configured"], bool)


def test_vercel_requests_require_the_shared_api_token() -> None:
    settings = Settings(
        _env_file=None,
        app_environment="production",
        database_url="postgresql://postgres:secret@pooler.example:6543/postgres",
        daybook_api_token="internal-test-token-that-is-long-enough",
    )
    with (
        patch("backend.app.main.get_settings", return_value=settings),
        TestClient(app) as client,
    ):
        denied = client.get("/api/health")
        allowed = client.get(
            "/api/health",
            headers={"x-daybook-api-token": "internal-test-token-that-is-long-enough"},
        )

    assert denied.status_code == 401
    assert denied.json() == {"detail": "Unauthorized."}
    assert allowed.status_code == 200

    settings.daybook_api_token = ""
    with (
        patch("backend.app.main.get_settings", return_value=settings),
        TestClient(app) as client,
    ):
        misconfigured = client.get("/api/health")
    assert misconfigured.status_code == 503
    assert misconfigured.json() == {
        "detail": "DAYBOOK_API_TOKEN is not securely configured."
    }


def test_configured_token_is_enforced_during_local_development() -> None:
    settings = Settings(
        _env_file=None,
        daybook_api_token="local-test-token-that-is-long-enough",
    )
    with (
        patch("backend.app.main.get_settings", return_value=settings),
        TestClient(app) as client,
    ):
        denied = client.get("/api/health")
        allowed = client.get(
            "/api/health",
            headers={"x-daybook-api-token": "local-test-token-that-is-long-enough"},
        )

    assert denied.status_code == 401
    assert allowed.status_code == 200


def test_deployed_demo_health_is_public_and_identifies_demo_mode() -> None:
    settings = Settings(
        _env_file=None,
        app_environment="production",
        daybook_demo_mode=True,
    )
    with (
        patch("backend.app.main.get_settings", return_value=settings),
        patch("backend.app.routers.health.get_settings", return_value=settings),
        TestClient(app) as client,
    ):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["mode"] == "demo"


def test_health_reports_independent_provider_capabilities() -> None:
    settings = Settings(
        _env_file=None,
        anthropic_api_key="configured-anthropic",
        alpaca_api_key_id="configured-alpaca",
        alpaca_api_secret_key="configured-alpaca-secret",
        finnhub_api_key="configured-finnhub",
    )
    with (
        patch("backend.app.main.get_settings", return_value=settings),
        patch("backend.app.routers.health.get_settings", return_value=settings),
        TestClient(app) as client,
    ):
        response = client.get("/api/health")

    capabilities = response.json()["capabilities"]
    assert capabilities["alpaca"] == {
        "configured": True,
        "enabled": True,
        "implemented": True,
        "state": "ready",
    }
    assert capabilities["anthropic"]["state"] == "pending_phase"
    assert capabilities["finnhub"]["state"] == "pending_phase"
    assert capabilities["tastytrade"]["state"] == "not_configured"

from backend.app.main import app
from fastapi.testclient import TestClient


def test_health_reports_database_and_config_booleans() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"]["configured"] is True
    assert payload["database"]["connected"] is True
    assert isinstance(payload["integrations"]["anthropic_configured"], bool)
    assert isinstance(payload["integrations"]["alpaca_configured"], bool)
    assert isinstance(payload["integrations"]["tastytrade_configured"], bool)
    assert isinstance(payload["integrations"]["finnhub_configured"], bool)


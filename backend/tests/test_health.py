from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "health" in data
    assert data["version"] == "0.1.0"


def test_health_endpoint_structure():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data
    assert "services" in data
    assert "database" in data["services"]
    assert "redis" in data["services"]
    assert "demo_mode" in data


def test_health_endpoint_healthy_state():
    with (
        patch("app.api_v1.health.check_db_connection", return_value=True),
        patch("app.api_v1.health.check_redis_connection", return_value=True),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["services"]["database"] == "connected"
        assert data["services"]["redis"] == "connected"


def test_health_endpoint_degraded_state():
    with (
        patch("app.api_v1.health.check_db_connection", return_value=False),
        patch("app.api_v1.health.check_redis_connection", return_value=True),
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["database"] == "disconnected"
        assert data["services"]["redis"] == "connected"

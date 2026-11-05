"""Automated tests for the GET /health endpoint."""

from __future__ import annotations


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "moatok-backend"
    assert payload["environment"] == "testing"
    assert payload["sharing_mode"] == "user_initiated_flutter"
    assert "timestamp" in payload

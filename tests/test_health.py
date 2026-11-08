"""Automated tests for the GET /health endpoint."""

from __future__ import annotations


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"

    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["service"] == "moatok-backend"
    assert payload["environment"] == "testing"
    assert payload["sharing_mode"] == "user_initiated_flutter"
    assert "timestamp" in payload


def test_chosun_proxy_uses_fixed_upstream(client, monkeypatch):
    from types import SimpleNamespace
    import json

    def fetch(url, **kwargs):
        assert url == 'https://chosun-daily-api-tv70.onrender.com/api/v1/articles?page=1&per_page=10'
        assert kwargs['max_redirects'] == 0
        return SimpleNamespace(status_code=200, content=json.dumps({'items': [{'id': n} for n in range(12)]}))

    monkeypatch.setattr('app.services.url_validator.fetch_and_validate_source_url', fetch)
    response = client.get('/api/v1/integrations/chosun-daily/articles')
    assert response.status_code == 200
    assert len(response.json['items']) == 10


def test_chosun_proxy_rejects_invalid_upstream(client, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr('app.services.url_validator.fetch_and_validate_source_url',
                        lambda *a, **k: SimpleNamespace(status_code=200, content='not json'))
    assert client.get('/api/v1/integrations/chosun-daily/articles').status_code == 502

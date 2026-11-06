from urllib.parse import urlsplit, parse_qs
from unittest.mock import MagicMock
import json


def configure(app):
    app.config.update(SECRET_KEY='test-secret', SESSION_COOKIE_SECURE=False,
                      KAKAO_REST_API_KEY='test-rest-key', KAKAO_REDIRECT_URI='https://api.example.com/api/v1/kakao/callback',
                      KAKAO_FRONTEND_ORIGIN='https://moatalk-e6fe1.web.app')


def test_not_configured_and_state_rejection(app, client):
    assert client.get('/api/v1/kakao/status').json == {'configured': False}
    assert client.get('/api/v1/kakao/login').status_code == 503
    configure(app)
    response = client.get('/api/v1/kakao/login')
    params = parse_qs(urlsplit(response.location).query)
    assert params['scope'] == ['talk_message']
    assert client.get('/api/v1/kakao/callback?state=wrong&code=code').status_code == 400


def test_code_exchange_and_replay_protection(app, client, monkeypatch):
    configure(app)
    response = client.get('/api/v1/kakao/login')
    state = parse_qs(urlsplit(response.location).query)['state'][0]
    mock = MagicMock()
    mock.__enter__.return_value.read.return_value = json.dumps({'access_token': 'test-token', 'expires_in': 3600, 'scope': 'talk_message'}).encode()
    monkeypatch.setattr('app.routes.kakao.urlopen', lambda *a, **k: mock)
    result = client.get('/api/v1/kakao/callback?state=' + state + '&code=example')
    assert result.status_code == 200
    assert 'test-token' in result.text
    assert 'no-store' in result.headers['Cache-Control']
    assert 'test-token' not in result.headers.get('Set-Cookie', '')
    assert client.get('/api/v1/kakao/callback?state=' + state + '&code=example').status_code == 400

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


def test_kakao_signin_creates_firebase_identity_and_reuses_connection(app, client, monkeypatch):
    configure(app)
    response = client.get('/api/v1/kakao/signin')
    state = parse_qs(urlsplit(response.location).query)['state'][0]
    tokens = {'access_token': 'private-access', 'refresh_token': 'private-refresh', 'expires_in': 3600, 'scope': 'talk_message'}
    responses = []
    for data in (tokens, {'id': 12345}):
        mock = MagicMock()
        mock.__enter__.return_value.read.return_value = json.dumps(data).encode()
        responses.append(mock)
    monkeypatch.setattr('app.routes.kakao.urlopen', lambda *a, **k: responses.pop(0))
    mint = MagicMock(return_value=b'firebase-custom-token')
    monkeypatch.setattr('app.routes.kakao.firebase_auth.create_custom_token', mint)
    result = client.get('/api/v1/kakao/callback?state=' + state + '&code=example')
    assert result.status_code == 200
    assert 'firebase-custom-token' in result.text
    assert 'private-access' not in result.text
    assert 'private-refresh' not in result.text
    mint.assert_called_once_with('kakao:12345', {'login_provider': 'kakao'})
    from app.services.my_chat_automation import accounts
    with app.app_context():
        account = accounts().document('kakao:12345').get().to_dict()
        assert account['credentials']
        assert not account.get('on_new') and not account.get('daily')
    assert client.get('/api/v1/kakao/callback?state=' + state + '&code=example').status_code == 400


def test_signin_forged_state_does_not_mint_identity(app, client, monkeypatch):
    configure(app)
    client.get('/api/v1/kakao/signin')
    mint = MagicMock()
    monkeypatch.setattr('app.routes.kakao.firebase_auth.create_custom_token', mint)
    assert client.get('/api/v1/kakao/callback?state=forged&code=example').status_code == 400
    mint.assert_not_called()

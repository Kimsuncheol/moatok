from datetime import datetime, timezone
from unittest.mock import Mock

from app.services import my_chat_automation as service


def test_encrypted_credentials_and_refresh(app, monkeypatch):
    with app.app_context():
        app.config['SECRET_KEY'] = 'test-secret'
        app.config['KAKAO_REST_API_KEY'] = 'test-key'
        service.store_tokens('alice', {'access_token': 'secret-access', 'refresh_token': 'secret-refresh', 'expires_in': 0})
        account = service.accounts().document('alice').get().to_dict()
        assert 'secret-access' not in account['credentials']
        assert 'secret-refresh' not in account['credentials']
        refresh = Mock(return_value={'access_token': 'renewed', 'expires_in': 3600})
        monkeypatch.setattr(service, 'post', refresh)
        assert service.access_token('alice', account) == 'renewed'
        renewed = service.accounts().document('alice').get().to_dict()
        assert 'secret-refresh' in service.cipher().decrypt(renewed['credentials'].encode()).decode()


def test_delivery_claim_prevents_duplicates_and_uncertain_retry(app, monkeypatch):
    with app.app_context():
        ref = service.accounts().document('alice')
        ref.set({})
        monkeypatch.setattr(service, 'access_token', lambda *args: 'access')
        send = Mock(return_value={'result_code': 0})
        monkeypatch.setattr(service, 'post', send)
        assert service.deliver(ref, {}, 'new:one', 'Hello')
        assert not service.deliver(ref, {}, 'new:one', 'Hello')
        assert send.call_count == 1
        send.side_effect = TimeoutError()
        assert not service.deliver(ref, {}, 'new:two', 'Hello')
        assert not service.deliver(ref, {}, 'new:two', 'Hello')
        assert send.call_count == 2


def test_automation_requires_auth(client):
    assert client.get('/api/v1/kakao/automation').status_code == 401
    assert client.post('/api/v1/kakao/automation/connect').status_code == 401
    assert client.post('/api/v1/kakao/automation/run').status_code == 401


def test_both_triggers_and_daily_time(app, monkeypatch):
    from types import SimpleNamespace
    now = datetime(2026, 11, 7, 0, 0, tzinfo=timezone.utc)
    account = {'credentials': 'encrypted', 'on_new': True, 'daily': True, 'daily_time': '09:00', 'enabled_at': now}
    ref = Mock(id='alice')
    ref.get.return_value.to_dict.return_value = account
    snapshot = SimpleNamespace(reference=ref, to_dict=lambda: account)
    private = Mock()
    private.stream.return_value = [snapshot]
    monkeypatch.setattr(service, 'accounts', lambda: private)
    message = SimpleNamespace(id='one', to_dict=lambda: {'body': 'Hello', 'status': 'pending'})
    db = Mock()
    db.collection.return_value.where.return_value.order_by.return_value.stream.return_value = [message]
    monkeypatch.setattr(service, 'get_firestore_client', lambda: db)
    send = Mock(return_value=True)
    monkeypatch.setattr(service, 'deliver', send)
    with app.app_context():
        assert service.run_automations(now) == {'sent': 2}
        assert [call.args[2] for call in send.call_args_list] == ['new:one', 'daily:2026-11-07']
        send.reset_mock()
        account['daily_time'] = '10:00'
        assert service.run_automations(now) == {'sent': 1}
        account['on_new'] = False
        send.reset_mock()
        assert service.run_automations(now) == {'sent': 0}
        send.assert_not_called()


def test_connect_unconfigured_and_configured(app, client, mock_firebase_auth):
    from test_kakao_oauth import configure
    headers = {'Authorization': 'Bearer valid-token-user-1'}
    assert client.post('/api/v1/kakao/automation/connect', headers=headers).status_code == 503
    configure(app)
    result = client.post('/api/v1/kakao/automation/connect', headers=headers)
    assert result.status_code == 200
    assert 'automation=' in result.json['url']


def test_cannot_enable_without_credentials(client, mock_firebase_auth):
    response = client.put('/api/v1/kakao/automation', headers={'Authorization': 'Bearer valid-token-user-1'},
                          json={'on_new': True, 'daily': False, 'daily_time': '09:00'})
    assert response.status_code == 409

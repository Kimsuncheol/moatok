"""Only authenticated Kakao webhooks may confirm browser-local share receipts."""
from datetime import datetime, timedelta, timezone

RECEIPT = 'a' * 64
PATH = '/api/v1/kakao/share'


def test_callback_requires_configuration_and_authentication(app, client):
    assert client.post(PATH + '/callback').status_code == 503
    app.config['KAKAO_ADMIN_KEY'] = 'test-admin-key'
    assert client.post(PATH + '/callback').status_code == 401
    assert client.get(PATH + '/receipts/not-a-receipt').status_code == 400


def test_verified_delivery_is_idempotent_and_private(app, client, fake_db):
    app.config['KAKAO_ADMIN_KEY'] = 'test-admin-key'
    url = PATH + '/receipts/' + RECEIPT
    assert client.get(url).json['delivered'] is False
    headers = {'Authorization': 'KakaoAK test-admin-key', 'X-Kakao-Resource-ID': 'resource-1'}
    body = {'receipt_id': RECEIPT, 'CHAT_TYPE': 'OpenMultiChat', 'HASH_CHAT_ID': 'private-room'}
    assert client.post(PATH + '/callback', data=body, headers=headers).status_code == 204
    result = client.get(url)
    assert result.json['delivered'] is True
    assert 'no-store' in result.headers['Cache-Control']
    first = result.json['delivered_at']
    assert client.post(PATH + '/callback', json=body, headers=headers).status_code == 204
    assert client.get(url).json['delivered_at'] == first
    stored = fake_db.collection('kakao_share_receipts').document(RECEIPT).get().to_dict()
    assert set(stored) == {'delivered_at', 'expires_at'}
    fake_db.collection('kakao_share_receipts').document(RECEIPT).update({'expires_at': datetime.now(timezone.utc) - timedelta(seconds=1)})
    assert client.get(url).json['delivered'] is False


def test_malformed_callback_cannot_confirm(app, client):
    app.config['KAKAO_ADMIN_KEY'] = 'test-admin-key'
    headers = {'Authorization': 'KakaoAK test-admin-key', 'X-Kakao-Resource-ID': 'resource-1'}
    for body in [[], {}, {'receipt_id': RECEIPT, 'CHAT_TYPE': 'invalid', 'HASH_CHAT_ID': 'room'}]:
        assert client.post(PATH + '/callback', json=body, headers=headers).status_code == 400
    assert client.get(PATH + '/receipts/' + RECEIPT).json['delivered'] is False

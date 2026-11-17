import json
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.request import Request

import pytest

from app.services.english_schedule import ScheduleError, validate_schedule, cloud_schedule

PATH = '/api/v1/admin/integrations/english-scrapper/schedule'
SCHEDULE = {'enabled': True, 'hour': 9, 'minute': 30, 'timezone': 'Asia/Seoul', 'weekdays': [0,1,2,3,4]}
HEADERS = {'Authorization': 'Bearer valid-token-admin'}


def test_schedule_requires_moatok_administrator(client, mock_firebase_auth, monkeypatch):
    invoke = Mock(return_value={**SCHEDULE, 'next_scheduled_at': None})
    monkeypatch.setattr('app.services.english_schedule.cloud_schedule', invoke)
    for method in ['GET', 'PUT']:
        assert client.open(PATH, method=method, json=SCHEDULE).status_code == 401
        assert client.open(PATH, method=method, json=SCHEDULE, headers={'Authorization':'Bearer valid-token-user-1'}).status_code == 403
    invoke.assert_not_called()
    result = client.put(PATH, headers=HEADERS, json=SCHEDULE)
    assert result.status_code == 200 and result.json['hour'] == 9
    invoke.assert_called_once_with('PUT', SCHEDULE)
    assert client.get(PATH, headers=HEADERS).status_code == 200


@pytest.mark.parametrize('change', [{'enabled':'true'}, {'hour':24}, {'hour':True}, {'minute':-1},
    {'weekdays':[]}, {'weekdays':[0,0]}, {'weekdays':[False]}, {'weekdays':[7]},
    {'timezone':'Invalid/Zone'}, {'target':'https://evil.example'}])
def test_schedule_validation(change):
    with pytest.raises(ScheduleError) as exc:
        validate_schedule({**SCHEDULE, **change})
    assert exc.value.status == 400


def test_backend_attaches_its_own_iam_identity_and_secret(app, monkeypatch):
    from app.services import english_schedule
    outgoing = []
    def open_request(request, timeout):
        outgoing.append(request)
        return None
    def fetch(url, **options):
        options['http_open'](Request(url), 120)
        assert options['max_redirects'] == 0
        return SimpleNamespace(status_code=200, content=json.dumps({**SCHEDULE,'next_scheduled_at':None}).encode())
    monkeypatch.setattr(english_schedule, 'fetch_and_validate_source_url', fetch)
    monkeypatch.setattr(english_schedule, '_default_urlopen', open_request)
    identity = Mock(return_value='google-service-id-token')
    monkeypatch.setattr(english_schedule.id_token, 'fetch_id_token', identity)
    with app.app_context():
        app.config['ENGLISH_SCRAPER_URL'] = 'https://scraper-example-uc.a.run.app'
        app.config['ENGLISH_SCRAPER_SCHEDULE_TOKEN'] = 'server-only-secret'
        result = cloud_schedule('PUT', SCHEDULE)
    assert outgoing[0].get_header('Authorization') == 'Bearer google-service-id-token'
    assert outgoing[0].get_header('X-schedule-token') == 'server-only-secret'
    assert json.loads(outgoing[0].data) == SCHEDULE
    assert outgoing[0].method == 'PUT'
    assert 'secret' not in json.dumps(result)
    assert identity.call_args.args[1] == 'https://scraper-example-uc.a.run.app'


def test_no_secret_fails_closed_without_network(app, monkeypatch):
    network = Mock()
    monkeypatch.setattr('app.services.english_schedule.fetch_and_validate_source_url', network)
    with app.app_context():
        app.config['ENGLISH_SCRAPER_SCHEDULE_TOKEN'] = ''
        with pytest.raises(ScheduleError) as exc:
            cloud_schedule('PUT', SCHEDULE)
        assert exc.value.status == 503
    network.assert_not_called()


def test_provider_failure_does_not_claim_saved(client, mock_firebase_auth, monkeypatch):
    def fail(*args):
        raise ScheduleError('Refresh before retrying.', 503)
    monkeypatch.setattr('app.services.english_schedule.cloud_schedule', fail)
    result = client.put(PATH, headers=HEADERS, json=SCHEDULE)
    assert result.status_code == 503
    assert result.json['error'] == 'scraper_schedule_unavailable'

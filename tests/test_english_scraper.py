from copy import deepcopy

from app.services.english_scraper import CORE, prepare_lesson, sync_english_lessons


def lesson():
    return {'id': 'lesson-1', 'canonical_url': 'https://www.chosun.com/english/one/',
            'updated_at': '2026-11-06T00:00:00Z', 'payload': {
                'article': {'title': 'English'},
                'lesson': {'fields': {key: {'text': 'A: Hello\nB: Hi'} for key in CORE}},
                'ocr': {'raw_text': 'Hello'}, 'processing': {'ocr_status': 'ok'}}}


class Client:
    def __init__(self, value):
        self.value = value

    def list_articles(self, offset=0):
        return {'items': [{'id': 'lesson-1'}], 'total': 2}

    def get_article(self, external_id):
        return deepcopy(self.value)


def test_readiness_preserves_lines_and_holds_uncertain_ocr():
    saved = lesson()
    assert not prepare_lesson(saved)['missing_sections']
    assert 'A: Hello\nB: Hi' in prepare_lesson(saved)['body']
    saved['payload']['processing']['ocr_status'] = 'low_confidence'
    assert 'ocr_quality' in prepare_lesson(saved)['missing_sections']
    saved['payload']['lesson']['fields']['expression']['text'] = '[unreadable]'
    assert 'expression' in prepare_lesson(saved)['missing_sections']


def test_replay_and_partial_retry_create_exactly_one_message(app, fake_db):
    with app.app_context():
        saved = lesson()
        saved['payload']['lesson']['fields'].pop('korean_meaning')
        client = Client(saved)
        assert sync_english_lessons(client=client, db=fake_db, notify=False)['held'] == 1
        client.value = lesson()
        result = sync_english_lessons(client=client, db=fake_db, notify=False)
        assert result['created'] == 1
        assert result['next_offset'] == 1
        result = sync_english_lessons(client=client, db=fake_db, notify=False)
        assert result['duplicate'] == 1
        assert result['created'] == 0


def test_failed_detail_keeps_error_visible(app, fake_db):
    with app.app_context():
        result = sync_english_lessons(client=Client({'id': 'bad'}), db=fake_db, notify=False)
        assert result['failed'] == 1
        assert result['errors'][0]['id'] == 'lesson-1'


def test_integration_admin_authorization_and_validation(client, mock_firebase_auth):
    base = '/api/v1/admin/integrations/english-scrapper'
    for method, suffix in [('GET', ''), ('GET', '/lessons'), ('POST', '/sync')]:
        assert client.open(base + suffix, method=method).status_code == 401
        assert client.open(base + suffix, method=method,
                           headers={'Authorization': 'Bearer valid-token-user-1'}).status_code == 403
    headers = {'Authorization': 'Bearer valid-token-admin'}
    assert client.get(base, headers=headers).status_code == 200
    assert client.post(base + '/sync', headers=headers, json={'offset': -1}).status_code == 400
    assert client.get('/api/v1/share-messages/missing/english-lesson').status_code == 401


def test_fetch_url_validates_and_imports(client, mock_firebase_auth, monkeypatch):
    from app.services.english_scraper import EnglishScraperClient
    calls = []
    def scrape(self, url):
        calls.append(url)
        return lesson()
    monkeypatch.setattr(EnglishScraperClient, 'scrape_article', scrape)
    headers = {'Authorization': 'Bearer valid-token-admin'}
    path = '/api/v1/admin/integrations/english-scrapper/fetch'
    assert client.post(path, json={'url': 'https://localhost/test'}, headers=headers).status_code == 400
    assert calls == []
    assert client.post('/api/v1/share-messages/english-lessons/fetch',
                       json={'url': 'https://localhost/test'}).status_code == 400
    result = client.post('/api/v1/share-messages/english-lessons/fetch', json={'url': 'https://www.chosun.com/test', 'title': 'Custom', 'note': 'My note'})
    assert result.status_code == 200
    assert result.json['status'] in ('created', 'duplicate')
    message = client.get('/api/v1/share-messages/' + result.json['message_id'], headers=headers).json
    assert message['share_message']['title'] == 'Custom'
    assert message['share_message']['body'].startswith('My note\n\n')
    assert client.post(path, json={'url': 'https://www.chosun.com/test'}, headers=headers).json['status'] == 'duplicate'

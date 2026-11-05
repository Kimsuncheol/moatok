"""Import saved English lessons; extraction stays in the upstream service."""
import hashlib
import json
from urllib.parse import quote, urlsplit

from flask import current_app

from app.extensions import get_firestore_client
from app.models import ValidationError
from app.repositories.articles_repo import ArticleRepository
from app.repositories.share_messages_repo import ShareMessageRepository
from app.repositories.firestore_utils import utc_now
from app.services.url_validator import fetch_and_validate_source_url
from app.services.notification_service import notify_pending_share_message

CORE = ('expression', 'korean_meaning', 'korean_explanation',
        'english_dialogue', 'korean_dialogue_translation')


class EnglishScraperClient:
    def __init__(self):
        self.base = current_app.config['ENGLISH_SCRAPER_URL'].rstrip('/')
        parsed = urlsplit(self.base)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValidationError('English scraper requires a public HTTPS base URL.')
        self.host = parsed.hostname

    def get(self, path):
        probe = fetch_and_validate_source_url(
            self.base + path, allowed_domains=(self.host,),
            timeout_seconds=20, max_bytes=2 * 1024 * 1024, max_redirects=0)
        if probe.status_code != 200:
            raise ValidationError('English scraper request failed.')
        try:
            return json.loads(probe.content)
        except (ValueError, UnicodeError) as exc:
            raise ValidationError('Invalid English scraper JSON response.') from exc

    def list_articles(self, offset=0, limit=20):
        page = self.get(f'/api/v1/articles?limit={limit}&offset={offset}')
        if not isinstance(page, dict) or not isinstance(page.get('items'), list):
            raise ValidationError('Invalid English scraper article page.')
        return page

    def get_article(self, external_id):
        return self.get('/api/v1/articles/' + quote(external_id, safe=''))

    def get_job_status(self):
        return self.get('/api/v1/jobs/status')


def prepare_lesson(saved):
    """Keep structured content and only share complete, readable lessons."""
    if not isinstance(saved, dict) or not isinstance(saved.get('payload'), dict):
        raise ValidationError('Invalid saved lesson.')
    payload = saved['payload']
    external_id = saved.get('id')
    if not isinstance(external_id, str) or not external_id.strip():
        raise ValidationError('Saved lesson ID is required.')
    fields = (payload.get('lesson') or {}).get('fields') or {}
    texts = {key: str((value or {}).get('text') or '').strip()
             for key, value in fields.items() if isinstance(value, dict)}
    missing = [key for key in CORE if not texts.get(key) or '[unreadable]' in texts[key].lower()]
    if not (payload.get('ocr') or {}).get('raw_text', '').strip():
        missing.append('transcript')
    if (payload.get('processing') or {}).get('ocr_status') != 'ok':
        missing.append('ocr_quality')
    article = payload.get('article') or {}
    url = str(saved.get('canonical_url') or article.get('url') or '')
    title = str(texts.get('expression') or article.get('title') or '').strip()
    if not title:
        raise ValidationError('Lesson title is required.')
    # Bound individual sections while retaining dialogue line breaks.
    lines = ['[오늘의 영어] ' + title[:100]]
    for key in ('korean_meaning', 'english_dialogue'):
        if texts.get(key):
            lines.append(texts[key][:120])
    lines.append(url)
    if len(json.dumps(texts, ensure_ascii=False).encode()) > 700_000:
        raise ValidationError('Lesson fields exceed the import size limit.')
    revision = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return dict(external_id=external_id, title=title[:100], body='\n\n'.join(lines),
                url=url, fields=texts, missing_sections=missing, revision=revision,
                upstream_updated_at=saved.get('updated_at'))


def sync_english_lessons(*, client=None, db=None, offset=0, notify=True):
    """Bounded offset scan. Explicit continuation avoids silently skipping history.

    Replays are intentional: the upstream API has no incremental cursor yet.
    Message IDs remain stable and existing reviewed/shared messages are preserved.
    """
    client = client or EnglishScraperClient()
    db = db or get_firestore_client()
    from app.repositories.devices_repo import UserDeviceRepository
    users = UserDeviceRepository(db=db).list_active_user_ids() if notify else []
    state = db.collection('integration_status').document('english_scrapper')
    if offset is None:
        previous = state.get()
        offset = (previous.to_dict() or {}).get('next_offset') or 0
    article_repo = ArticleRepository(db=db)
    share_repo = ShareMessageRepository(db=db)
    stats = dict(processed=0, created=0, duplicate=0, held=0, failed=0)
    errors = []
    try:
        page = client.list_articles(offset=offset)
        items = page['items']
        if not isinstance(items, list) or len(items) > 100 or any(not isinstance(item, dict) for item in items):
            raise ValidationError('Invalid English scraper page.')
    except Exception:
        state.set({'error': 'upstream_unavailable', 'next_offset': offset,
                   'checked_at': utc_now().isoformat()}, merge=True)
        raise
    for item in items:
        try:
            saved = client.get_article(str(item['id']))
            lesson = prepare_lesson(saved)
            if lesson['external_id'] != item['id']:
                raise ValidationError('Lesson ID differs from listing.')
            article, _ = article_repo.create_or_get_with_status(
                source_id='english_scrapper', source_url=current_app.config['ENGLISH_SCRAPER_URL'],
                canonical_url=lesson['url'], stable_id=lesson['external_id'],
                title=lesson['title'], summary=lesson['fields'].get('korean_meaning'),
                published_at=(saved['payload'].get('article') or {}).get('published_at'))
            # Snapshot revisions separately; never overwrite user-edited share text.
            db.collection('english_lessons').document(article['id']).set({
                **lesson, 'article_id': article['id'], 'synced_at': utc_now()})
            stats['processed'] += 1
            if lesson['missing_sections']:
                stats['held'] += 1
                continue
            message, created = share_repo.create_or_get_with_status(
                article_id=article['id'], title=lesson['title'], body=lesson['body'],
                target_url=lesson['url'], status='pending')
            stats['created' if created else 'duplicate'] += 1
            if notify and users and message.get('status') == 'pending' and share_repo.claim_initial_notification(message['id']):
                notify_pending_share_message(message, share_repo=share_repo, target_user_ids=users)
        except Exception:
            current_app.logger.exception('English lesson import failed')
            stats['failed'] += 1
            errors.append({'id': str(item.get('id', '')), 'code': 'lesson_import_failed'})
    scanned = offset + len(items)
    next_offset = scanned if items and scanned < int(page.get('total', scanned)) else None
    result = {**stats, 'offset': offset, 'next_offset': next_offset, 'errors': errors,
              'checked_at': utc_now().isoformat()}
    state.set(result)
    return result

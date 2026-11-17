"""Moatok's authenticated server-to-server schedule bridge."""
import json
from urllib.error import HTTPError
from urllib.request import Request
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from flask import current_app
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token

from app.services.url_validator import fetch_and_validate_source_url, _default_urlopen


class ScheduleError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def validate_schedule(value):
    required = {'enabled', 'hour', 'minute', 'timezone', 'weekdays'}
    if not isinstance(value, dict) or set(value) != required:
        raise ScheduleError('Send enabled, hour, minute, timezone, and weekdays.', 400)
    if type(value['enabled']) is not bool or type(value['hour']) is not int or type(value['minute']) is not int:
        raise ScheduleError('Schedule time and enabled state are invalid.', 400)
    if not 0 <= value['hour'] <= 23 or not 0 <= value['minute'] <= 59:
        raise ScheduleError('Schedule time is outside its supported range.', 400)
    days = value['weekdays']
    if not isinstance(days, list) or not 1 <= len(days) <= 7 or any(type(day) is not int or day not in range(7) for day in days) or len(set(days)) != len(days):
        raise ScheduleError('Use unique weekdays from 0 (Monday) to 6 (Sunday).', 400)
    try:
        if not isinstance(value['timezone'], str) or len(value['timezone']) > 100:
            raise ValueError()
        ZoneInfo(value['timezone'])
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ScheduleError('Use a valid IANA timezone.', 400) from None
    return {**value, 'weekdays': sorted(days)}


def scraper_identity_headers(base):
    if not urlsplit(base).hostname.endswith('.run.app'):
        return {}
    # The audience is always the configured service origin, never client input.
    token = id_token.fetch_id_token(GoogleRequest(), base)
    return {'Authorization': 'Bearer ' + token}


def cloud_schedule(method='GET', payload=None):
    base = current_app.config['ENGLISH_SCRAPER_URL'].rstrip('/')
    parsed = urlsplit(base)
    token = current_app.config.get('ENGLISH_SCRAPER_SCHEDULE_TOKEN', '')
    if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or not token:
        raise ScheduleError('Scraper schedule integration is not configured.', 503)
    body = validate_schedule(payload) if method == 'PUT' else None
    try:
        headers = {**scraper_identity_headers(base), 'X-Schedule-Token': token, 'Content-Type': 'application/json'}
        def send(request, timeout):
            return _default_urlopen(Request(request.full_url, method=method, headers=headers,
                data=json.dumps(body).encode() if body is not None else None), timeout)
        probe = fetch_and_validate_source_url(base + '/api/v1/jobs/schedule',
            allowed_domains=(parsed.hostname,), max_redirects=0, max_bytes=64_000,
            timeout_seconds=120, http_open=send)
        if probe.status_code != 200:
            raise ScheduleError('Scraper schedule could not be saved. Refresh before retrying.')
        result = json.loads(probe.content)
        # Verify the provider response; never return arbitrary upstream JSON.
        settings = validate_schedule({key: result[key] for key in ('enabled','hour','minute','timezone','weekdays')})
        return {**settings, 'next_scheduled_at': result.get('next_scheduled_at')}
    except ScheduleError:
        raise
    except HTTPError as exc:
        status = 503 if exc.code == 503 else 409 if exc.code == 409 else 502
        raise ScheduleError('Scraper schedule request failed. Refresh before retrying.', status) from None
    except Exception:
        raise ScheduleError('Scraper schedule is unavailable. Refresh before retrying.', 503) from None

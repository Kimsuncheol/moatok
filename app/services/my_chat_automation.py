"""Opt-in My Chat delivery. Private encrypted credentials never enter API responses."""
import base64
import hashlib
import json
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.fernet import Fernet
from flask import current_app
from google.api_core.exceptions import AlreadyExists
from app.extensions import get_firestore_client


def cipher():
    secret = current_app.config['SECRET_KEY']
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(('my-chat:' + secret).encode()).digest()))


def accounts():
    return get_firestore_client().collection('private_my_chat_accounts')


def post(url, data, token=None):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, data=urlencode(data).encode(), headers=headers, method='POST'), timeout=15) as response:
        return json.load(response)


def store_tokens(uid, tokens):
    ref = accounts().document(uid)
    previous = ref.get().to_dict() or {}
    if not tokens.get('refresh_token') and previous.get('credentials'):
        old = json.loads(cipher().decrypt(previous['credentials'].encode()))
        tokens['refresh_token'] = old['refresh_token']
    tokens['expires_at'] = time.time() + tokens['expires_in'] - 60
    ref.set({'credentials': cipher().encrypt(json.dumps(tokens).encode()).decode(), 'error': ''}, merge=True)


def access_token(uid, account):
    tokens = json.loads(cipher().decrypt(account['credentials'].encode()))
    if time.time() >= tokens['expires_at']:
        data = {'grant_type': 'refresh_token', 'client_id': current_app.config['KAKAO_REST_API_KEY'], 'refresh_token': tokens['refresh_token']}
        if current_app.config.get('KAKAO_CLIENT_SECRET'):
            data['client_secret'] = current_app.config['KAKAO_CLIENT_SECRET']
        renewed = post('https://kauth.kakao.com/oauth/token', data)
        renewed.setdefault('refresh_token', tokens['refresh_token'])
        store_tokens(uid, renewed)
        tokens = renewed
    return tokens['access_token']


def deliver(ref, account, key, text):
    # Claim before external I/O: ambiguous failures are held for review, never retried blindly.
    receipt = ref.collection('deliveries').document(hashlib.sha256(key.encode()).hexdigest())
    try:
        receipt.create({'status': 'claimed', 'created_at': datetime.now(timezone.utc)})
    except AlreadyExists:
        return False
    try:
        token = access_token(ref.id, account)
        link = current_app.config['KAKAO_FRONTEND_ORIGIN'].rstrip('/') + '/'
        template = {'object_type': 'text', 'text': text[:200], 'link': {'web_url': link, 'mobile_web_url': link}, 'button_title': '모아톡 열기'}
        result = post('https://kapi.kakao.com/v2/api/talk/memo/default/send', {'template_object': json.dumps(template)}, token)
        if result.get('result_code') != 0:
            raise ValueError('Delivery not confirmed')
        receipt.update({'status': 'sent'})
        ref.update({'error': ''})
        return True
    except Exception:
        receipt.update({'status': 'review_required'})
        ref.update({'error': '전송 결과를 확인할 수 없습니다. 카카오 연결과 채팅방을 확인해 주세요.'})
        return False


def run_automations(now=None):
    now = now or datetime.now(timezone.utc)
    db = get_firestore_client()
    sent = 0
    for snapshot in accounts().stream():
        account = snapshot.to_dict() or {}
        if not account.get('credentials') or not (account.get('on_new') or account.get('daily')):
            continue
        ref = snapshot.reference
        start = account.get('enabled_at', now)
        messages = []
        collection = current_app.config.get('FIRESTORE_COLLECTION_SHARE_MESSAGES', 'share_messages')
        for doc in db.collection(collection).where('created_at', '>=', start).order_by('created_at').stream():
            message = doc.to_dict() or {}
            if message.get('body') and message.get('status') != 'failed' and message.get('fetch_status') != 'failed':
                messages.append((doc.id, message))
        if account.get('on_new'):
            for mid, message in messages:
                sent += deliver(ref, account, 'new:' + mid, message['body'])
                account = ref.get().to_dict() or account
        local = now.astimezone(ZoneInfo('Asia/Seoul'))
        if account.get('daily') and local.strftime('%H:%M') >= account.get('daily_time', '09:00'):
            text = '모아톡 오늘의 모음\n' + '\n\n'.join(m['body'] for _, m in messages[-5:])
            if messages:
                sent += deliver(ref, account, 'daily:' + local.date().isoformat(), text)
    return {'sent': sent}

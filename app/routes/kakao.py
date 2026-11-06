"""Kakao OAuth code exchange. No token is stored in cookies or URLs."""
import json
import secrets
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, current_app, jsonify, redirect, request, session

kakao_bp = Blueprint('kakao', __name__, url_prefix='/api/v1/kakao')


def ready():
    return all(current_app.config.get(key) for key in (
        'SECRET_KEY', 'KAKAO_REST_API_KEY', 'KAKAO_REDIRECT_URI', 'KAKAO_FRONTEND_ORIGIN'))


@kakao_bp.get('/status')
def status():
    return jsonify(configured=ready())


@kakao_bp.get('/login')
def login():
    if not ready():
        return jsonify(error='kakao_not_configured'), 503
    state = secrets.token_urlsafe(32)
    session['kakao_state'] = state
    session['kakao_started'] = time.time()
    return redirect('https://kauth.kakao.com/oauth/authorize?' + urlencode({
        'client_id': current_app.config['KAKAO_REST_API_KEY'],
        'redirect_uri': current_app.config['KAKAO_REDIRECT_URI'],
        'response_type': 'code', 'scope': 'talk_message', 'state': state}))


@kakao_bp.get('/callback')
def callback():
    if not ready():
        return jsonify(error='kakao_not_configured'), 503
    state = session.pop('kakao_state', '')
    started = session.pop('kakao_started', 0)
    if not state or not secrets.compare_digest(state, request.args.get('state', '')) or time.time() - started > 600:
        return jsonify(error='invalid_oauth_state'), 400
    result = {'type': 'moatok-kakao-login', 'error': '카카오 로그인이 취소되었거나 실패했습니다.'}
    if request.args.get('code') and not request.args.get('error'):
        data = {'grant_type': 'authorization_code', 'client_id': current_app.config['KAKAO_REST_API_KEY'],
                'redirect_uri': current_app.config['KAKAO_REDIRECT_URI'], 'code': request.args['code']}
        if current_app.config.get('KAKAO_CLIENT_SECRET'):
            data['client_secret'] = current_app.config['KAKAO_CLIENT_SECRET']
        try:
            req = Request('https://kauth.kakao.com/oauth/token', data=urlencode(data).encode(), method='POST')
            with urlopen(req, timeout=15) as response:
                token = json.load(response)
            if not token.get('access_token') or 'talk_message' not in token.get('scope', '').split():
                raise ValueError('Missing permission')
            result = {'type': 'moatok-kakao-login', 'access_token': token['access_token'], 'expires_in': token['expires_in']}
        except Exception:
            result['error'] = '카카오 연결에 실패했습니다. talk_message 동의 및 앱 설정을 확인하세요.'
    # Escape '<' to prevent an OAuth error or token from terminating the script.
    payload = json.dumps(result, ensure_ascii=True).replace('<', '\\u003c')
    origin = json.dumps(current_app.config['KAKAO_FRONTEND_ORIGIN']).replace('<', '\\u003c')
    nonce = secrets.token_urlsafe(24)
    html = f'<!doctype html><meta charset="utf-8"><p>카카오 연결 처리가 끝났습니다. 이 창을 닫아 주세요.</p><script nonce="{nonce}">if(window.opener){{window.opener.postMessage({payload},{origin});window.close();}}</script>'
    return html, 200, {'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store',
                       'Content-Security-Policy': f"default-src 'none'; script-src 'nonce-{nonce}'", 'Referrer-Policy': 'no-referrer'}

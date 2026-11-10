"""Verified Kakao delivery receipts, including browser-local cards.

The random receipt is a read capability. Never store message text or recipients.
"""
import hmac
import re
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, request
from google.api_core.exceptions import AlreadyExists

from app.extensions import get_firestore_client

kakao_share_bp = Blueprint('kakao_share', __name__, url_prefix='/api/v1/kakao/share')
RECEIPT = re.compile(r'^[a-f0-9]{64}$')
CHAT_TYPES = {'MemoChat', 'DirectChat', 'MultiChat', 'OpenDirectChat', 'OpenMultiChat'}


@kakao_share_bp.post('/callback')
def delivery_callback():
    key = current_app.config.get('KAKAO_ADMIN_KEY')
    if not key:
        return jsonify(error='webhook_not_configured'), 503
    if not hmac.compare_digest(request.headers.get('Authorization', ''), f'KakaoAK {key}'):
        return jsonify(error='unauthorized'), 401
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data if isinstance(data, dict) or request.form else {}
    receipt = data.get('receipt_id', '')
    if (not isinstance(receipt, str) or not RECEIPT.fullmatch(receipt)
            or data.get('CHAT_TYPE') not in CHAT_TYPES or not data.get('HASH_CHAT_ID')
            or not request.headers.get('X-Kakao-Resource-ID')):
        return jsonify(error='invalid_receipt'), 400
    now = datetime.now(timezone.utc)
    try:
        get_firestore_client().collection('kakao_share_receipts').document(receipt).create({
            'delivered_at': now.isoformat(), 'expires_at': now + timedelta(days=1)
        })
    except AlreadyExists:
        pass  # Retries and multiple recipients must not change the first confirmation.
    return '', 204


@kakao_share_bp.get('/receipts/<receipt>')
def delivery_status(receipt):
    if not RECEIPT.fullmatch(receipt):
        return jsonify(error='invalid_receipt'), 400
    if not current_app.config.get('KAKAO_ADMIN_KEY'):
        return jsonify(error='webhook_not_configured'), 503
    snapshot = get_firestore_client().collection('kakao_share_receipts').document(receipt).get()
    data = snapshot.to_dict() or {}
    expires = data.get('expires_at')
    delivered = bool(expires and expires > datetime.now(timezone.utc))
    return jsonify(delivered=delivered, delivered_at=data.get('delivered_at') if delivered else None)

"""Opaque application sessions backed by Supabase.

Only a random session identifier reaches the browser. Supabase access and refresh
tokens are encrypted with the server-only SESSION_SECRET before storage.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from fastapi import HTTPException
from types import SimpleNamespace

from .config import get_settings
from .database import service_client
from .auth_transport import auth_request


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def csrf_for(raw_id: str) -> str:
    return hmac.new(get_settings().session_secret.encode(), ('csrf:' + raw_id).encode(), hashlib.sha256).hexdigest()


def _cipher() -> AESGCM:
    secret = get_settings().session_secret
    if len(secret) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
    return AESGCM(hashlib.sha256(secret.encode("utf-8")).digest())


def encrypt_tokens(access_token: str, refresh_token: str) -> str:
    nonce = secrets.token_bytes(12)
    payload = json.dumps({"access_token": access_token, "refresh_token": refresh_token}, separators=(",", ":")).encode()
    encrypted = _cipher().encrypt(nonce, payload, b"sisu-session-v1")
    return base64.urlsafe_b64encode(nonce + encrypted).decode()


def decrypt_tokens(value: str) -> tuple[str, str]:
    raw = base64.urlsafe_b64decode(value.encode())
    try:
        payload = json.loads(_cipher().decrypt(raw[:12], raw[12:], b"sisu-session-v1"))
    except InvalidTag:
        raise ValueError('Invalid encrypted session') from None
    return payload["access_token"], payload["refresh_token"]


@dataclass
class SessionData:
    raw_id: str
    row_id: str
    user_id: str
    access_token: str
    refresh_token: str
    csrf_hash: str
    expires_at: datetime


def create_session(user_id: str, access_token: str, refresh_token: str, token_expires_at: int | None) -> tuple[str, str]:
    settings = get_settings()
    raw_id = secrets.token_urlsafe(48)
    csrf = csrf_for(raw_id)
    now = datetime.now(timezone.utc)
    app_expiry = now + timedelta(seconds=settings.session_max_age_seconds)
    token_expiry = datetime.fromtimestamp(token_expires_at, timezone.utc) if token_expires_at else app_expiry
    expires_at = min(app_expiry, token_expiry + timedelta(days=7))
    row = {
        "session_hash": digest(raw_id), "user_id": user_id,
        "token_ciphertext": encrypt_tokens(access_token, refresh_token),
        "csrf_hash": digest(csrf), "expires_at": expires_at.isoformat(),
    }
    service_client().table("app_sessions").insert(row).execute()
    return raw_id, csrf


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_session(raw_id: str | None) -> SessionData:
    if not raw_id:
        raise HTTPException(401, "Authentication required")
    rows = (service_client().table("app_sessions").select("id,user_id,token_ciphertext,csrf_hash,expires_at,revoked_at")
            .eq("session_hash", digest(raw_id)).limit(1).execute().data)
    if not rows or rows[0].get("revoked_at"):
        raise HTTPException(401, "Invalid session")
    row = rows[0]
    expires_at = _parse_time(row["expires_at"])
    if expires_at <= datetime.now(timezone.utc):
        revoke_session(raw_id)
        raise HTTPException(401, "Session expired")
    try:
        access_token, refresh_token = decrypt_tokens(row["token_ciphertext"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Invalid session. Sign in again.') from None
    return SessionData(raw_id, row["id"], row["user_id"], access_token, refresh_token, row["csrf_hash"], expires_at)


def refresh_and_validate(session: SessionData):
    """Return a verified Auth user and refresh an expired Supabase JWT safely."""
    try:
        user = auth_request('GET', 'user', token=session.access_token)
        if user.get('id') == session.user_id:
            return SimpleNamespace(id=user['id'], email=user.get('email')), session.access_token
        raise HTTPException(401, 'Invalid session identity')
    except HTTPException as exc:
        if exc.status_code != 401:
            raise

    # A database row lock serializes refresh across workers, not merely threads.
    import psycopg
    settings = get_settings()
    if not settings.supabase_database_url:
        raise HTTPException(503, 'Session refresh is not configured. Contact the administrator.')
    invalid = False
    with psycopg.connect(settings.supabase_database_url, connect_timeout=10) as conn:
        row = conn.execute('select token_ciphertext, revoked_at, expires_at from public.app_sessions where id=%s for update',
                           (session.row_id,)).fetchone()
        if not row or row[1] or row[2] <= datetime.now(timezone.utc):
            raise HTTPException(401, 'Session expired')
        access, refresh = decrypt_tokens(row[0])
        # Another worker may already have rotated this session while we waited.
        try:
            user = auth_request('GET', 'user', token=access)
            if user.get('id') == session.user_id:
                return SimpleNamespace(id=user['id'], email=user.get('email')), access
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
        try:
            tokens = auth_request('POST', 'token', {'refresh_token': refresh}, params={'grant_type': 'refresh_token'})
            user = auth_request('GET', 'user', token=tokens['access_token'])
            if user.get('id') != session.user_id:
                raise HTTPException(401, 'Invalid session identity')
        except HTTPException as exc:
            if exc.status_code not in {400, 401}:
                raise
            conn.execute("update public.app_sessions set revoked_at=now(), token_ciphertext='revoked' where id=%s", (session.row_id,))
            invalid = True
        else:
            conn.execute('update public.app_sessions set token_ciphertext=%s,updated_at=now() where id=%s',
                         (encrypt_tokens(tokens['access_token'], tokens['refresh_token']), session.row_id))
    if invalid:
        raise HTTPException(401, 'Session expired. Sign in again.')
    return SimpleNamespace(id=user['id'], email=user.get('email')), tokens['access_token']


def revoke_session(raw_id: str) -> None:
    service_client().table("app_sessions").update({
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "token_ciphertext": "revoked",
    }).eq("session_hash", digest(raw_id)).execute()

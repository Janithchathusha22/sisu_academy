"""Browser receives only an opaque cookie. OAuth/PKCE and tokens stay server-side."""
import base64
import hashlib
import json
import secrets
import time
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, SecretStr, field_validator
from .auth_transport import auth_request
from .config import get_settings
from .database import user_client, service_client
from .dependencies import Principal, current_user
from .identity_context import load_identity
from .sessions import create_session, revoke_session, encrypt_tokens, decrypt_tokens, digest, load_session

router = APIRouter(prefix='/api/auth', tags=['authentication'])
FLOW_COOKIE = 'sisu_auth_flow'


class EmailInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)

    @field_validator('email')
    @classmethod
    def valid_email(cls, value):
        value = value.strip()
        if value.count('@') != 1 or '.' not in value.split('@')[-1] or any(c.isspace() for c in value):
            raise ValueError('Enter a valid email address')
        return value


class LoginInput(EmailInput):
    password: SecretStr = Field(min_length=1, max_length=256)


class SignupInput(LoginInput):
    full_name: str = Field(min_length=1, max_length=120)
    account_type: Literal['student', 'teacher', 'institute'] = 'student'
    country: str = Field(default='', max_length=80)
    timezone: str = Field(default='Asia/Colombo', max_length=80)
    organization: str = Field(default='', max_length=120)
    subject: str = Field(default='', max_length=120)


class PasswordInput(BaseModel):
    password: SecretStr = Field(min_length=8, max_length=256)


def require_origin(request: Request):
    if request.headers.get('origin') != get_settings().frontend_url.rstrip('/'):
        raise HTTPException(403, 'Untrusted request origin')


def require_configuration():
    try:
        get_settings().require_auth()
    except RuntimeError:
        raise HTTPException(503, 'Sign-in is not configured. Contact the site administrator.') from None


def _profile(token, user_id):
    profile = load_identity(user_client(token), user_id)
    if not profile:
        raise HTTPException(403, 'Profile provisioning is incomplete. Contact the site administrator.')
    return profile


def _set_cookie(response, raw_id, csrf):
    settings = get_settings()
    response.set_cookie(settings.session_cookie_name, raw_id, max_age=settings.session_max_age_seconds,
                        httponly=True, secure=settings.session_cookie_secure, samesite='lax', path='/')
    response.headers['Cache-Control'] = 'no-store'


def establish(tokens, request, response, recovery=False):
    # Always verify identity with Auth; never trust user metadata or an unverified JWT.
    user = auth_request('GET', 'user', token=tokens['access_token'])
    if not user.get('id') or not user.get('email_confirmed_at'):
        raise HTTPException(403, 'Confirm your email before signing in.')
    profile = _profile(tokens['access_token'], user['id'])
    old = request.cookies.get(get_settings().session_cookie_name)
    raw_id, csrf = create_session(user['id'], tokens['access_token'], tokens['refresh_token'], tokens.get('expires_at'))
    if old:
        revoke_session(old)
    _set_cookie(response, raw_id, csrf)
    return {'user': {'id': user['id'], 'email': user.get('email')}, 'profile': profile,
            'csrf_token': csrf, 'recovery': recovery}


def begin_flow(response, purpose):
    verifier, state = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    payload = json.dumps({'state': state, 'purpose': purpose, 'expires': time.time() + 3600})
    response.set_cookie(FLOW_COOKIE, encrypt_tokens(verifier, payload), max_age=3600,
                        httponly=True, secure=get_settings().session_cookie_secure, samesite='lax', path='/api/auth')
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    callback = get_settings().public_api_url.rstrip('/') + '/api/auth/callback?' + urlencode({'state': state})
    return challenge, callback


@router.post('/login', dependencies=[Depends(require_origin), Depends(require_configuration)])
def login(data: LoginInput, request: Request, response: Response):
    tokens = auth_request('POST', 'token', {'email': data.email, 'password': data.password.get_secret_value()}, params={'grant_type': 'password'})
    return establish(tokens, request, response)


@router.post('/signup', dependencies=[Depends(require_origin), Depends(require_configuration)])
def signup(data: SignupInput, request: Request, response: Response):
    if len(data.password.get_secret_value()) < 8:
        raise HTTPException(422, 'Use at least 8 characters for your password.')
    challenge, callback = begin_flow(response, 'signup')
    metadata = data.model_dump(exclude={'password', 'email'})
    result = auth_request('POST', 'signup', {'email': data.email, 'password': data.password.get_secret_value(),
                           'data': metadata, 'code_challenge': challenge, 'code_challenge_method': 's256'},
                          params={'redirect_to': callback})
    if result.get('access_token'):
        response.delete_cookie(FLOW_COOKIE, path='/api/auth')
        return establish(result, request, response)
    return {'confirmation_required': True, 'message': 'Check your email and open the link in this browser.'}


@router.post('/google/start', dependencies=[Depends(require_origin), Depends(require_configuration)])
def google(response: Response):
    challenge, callback = begin_flow(response, 'google')
    return {'url': get_settings().supabase_url.rstrip('/') + '/auth/v1/authorize?' + urlencode({
        'provider': 'google', 'redirect_to': callback, 'code_challenge': challenge, 'code_challenge_method': 's256'})}


@router.post('/password/reset', dependencies=[Depends(require_origin), Depends(require_configuration)])
def reset_password(data: EmailInput, response: Response):
    challenge, callback = begin_flow(response, 'recovery')
    auth_request('POST', 'recover', {'email': data.email, 'code_challenge': challenge, 'code_challenge_method': 's256'},
                 params={'redirect_to': callback})
    return {'message': 'If an account exists, a reset link will be sent. Open it in this browser.'}


@router.get('/callback', dependencies=[Depends(require_configuration)])
def callback(request: Request, code: str = '', state: str = ''):
    target = get_settings().frontend_url.rstrip('/') + '/'
    response = RedirectResponse(target, status_code=303, headers={'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer'})
    try:
        verifier, raw = decrypt_tokens(request.cookies.get(FLOW_COOKIE, ''))
        flow = json.loads(raw)
        if not code or not state or flow['expires'] < time.time() or not secrets.compare_digest(state, flow['state']):
            raise ValueError('Invalid flow')
        tokens = auth_request('POST', 'token', {'auth_code': code, 'code_verifier': verifier}, params={'grant_type': 'pkce'})
        establish(tokens, request, response)
        if flow['purpose'] == 'recovery':
            response.headers['location'] = target + '?recovery=1'
    except HTTPException as exc:
        response.headers['location'] = target + '?auth_error=' + ('unavailable' if exc.status_code == 503 else 'callback')
    except (ValueError, KeyError, TypeError):
        response.headers['location'] = target + '?auth_error=callback'
    finally:
        response.delete_cookie(FLOW_COOKIE, path='/api/auth')
    return response


@router.get('/session')
def session(request: Request, response: Response, user: Principal = Depends(current_user)):
    response.headers['Cache-Control'] = 'no-store'
    # Deterministic, secret-bound CSRF token survives reloads without cross-origin cookie reads.
    from .sessions import csrf_for
    return {'user': {'id': user.id, 'email': user.email}, 'profile': _profile(user.token, user.id),
            'csrf_token': csrf_for(user.session_id)}


@router.put('/password', dependencies=[Depends(require_origin)])
def password(data: PasswordInput, request: Request, response: Response, user: Principal = Depends(current_user)):
    auth_request('PUT', 'user', {'password': data.password.get_secret_value()}, token=user.token)
    # Changing a password invalidates all application sessions, including this one.
    from datetime import datetime, timezone
    service_client().table('app_sessions').update({'revoked_at': datetime.now(timezone.utc).isoformat(),
                                                 'token_ciphertext': 'revoked'}).eq('user_id', user.id).execute()
    response.delete_cookie(get_settings().session_cookie_name, path='/')
    return {'message': 'Password updated. Sign in with your new password.'}


@router.delete('/session', status_code=204, dependencies=[Depends(require_origin)])
def logout(request: Request):
    raw_id = request.cookies.get(get_settings().session_cookie_name)
    if raw_id:
        try:
            session_data = load_session(raw_id)
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
        else:
            csrf = request.headers.get('x-csrf-token', '')
            if not secrets.compare_digest(digest(csrf), session_data.csrf_hash):
                raise HTTPException(403, 'Invalid CSRF token')
            revoke_session(raw_id)
            try:
                auth_request('POST', 'logout', token=session_data.access_token, params={'scope': 'local'})
            except HTTPException:
                pass  # The app session is already irrevocably revoked.
    response = Response(status_code=204, headers={'Cache-Control': 'no-store'})
    response.delete_cookie(get_settings().session_cookie_name, path='/')
    response.delete_cookie('sisu_csrf', path='/')
    return response

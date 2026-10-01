"""Offline BFF regression tests. These do not prove live Supabase/RLS connectivity."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app import auth, auth_transport, config, database, dependencies, sessions
from app.main import app

ORIGIN = 'http://127.0.0.1:5178'
UID = '10000000-0000-0000-0000-000000000001'

class Store:
    def __init__(self):
        self.rows = []
    def table(self, name):
        assert name == 'app_sessions'
        store = self
        class Query:
            def __init__(self):
                self.mode='select'; self.filters={}; self.values={}
            def select(self, *args): return self
            def limit(self, *args): return self
            def eq(self, key, value): self.filters[key]=value; return self
            def insert(self, values): self.mode='insert'; self.values=values; return self
            def update(self, values): self.mode='update'; self.values=values; return self
            def execute(self):
                if self.mode=='insert':
                    store.rows.append({'id':str(len(store.rows)+1),'revoked_at':None,**self.values})
                matches=[r for r in store.rows if all(r.get(k)==v for k,v in self.filters.items())]
                if self.mode=='update':
                    for r in matches: r.update(self.values)
                return SimpleNamespace(data=matches)
        return Query()

@pytest.fixture
def env(monkeypatch):
    settings=config.Settings(_env_file=None, supabase_url='https://example.supabase.co',
        supabase_publishable_key='public-test-key',SUPABASE_SERVICE_ROLE_KEY='private-test-key',
        supabase_database_url='postgresql://invalid/test',session_secret='test-secret-'*5,
        frontend_url=ORIGIN,public_api_url=ORIGIN)
    for module in [auth,auth_transport,config,database,dependencies,sessions]:
        monkeypatch.setattr(module,'get_settings',lambda: settings)
    store=Store()
    monkeypatch.setattr(sessions,'service_client',lambda: store)
    monkeypatch.setattr(auth,'service_client',lambda: store)
    profile={'id':UID,'email':'student@example.test','full_name':'Test Student','role':'student',
             'institution_id':None,'account_status':'active'}
    monkeypatch.setattr(auth,'_profile',lambda token,uid: profile.copy())
    class ProfileQuery:
        def table(self,*a): return self
        def select(self,*a): return self
        def eq(self,*a): return self
        def limit(self,*a): return self
        def execute(self): return SimpleNamespace(data=[profile.copy()])
    monkeypatch.setattr(dependencies,'user_client',lambda token: ProfileQuery())
    calls=[]
    def transport(method,path,body=None,token=None,params=None):
        calls.append((method,path,body,params))
        if path=='token': return {'access_token':'access-test','refresh_token':'refresh-test'}
        if path=='user': return {'id':UID,'email':profile['email'],'email_confirmed_at':'2026-01-01'}
        return {}
    monkeypatch.setattr(auth,'auth_request',transport)
    monkeypatch.setattr(sessions,'auth_request',transport)
    with TestClient(app,base_url=ORIGIN) as client:
        yield SimpleNamespace(client=client,settings=settings,store=store,profile=profile,calls=calls)

def login(env):
    response=env.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':'student@example.test','password':'valid-password'})
    assert response.status_code==200, response.text
    return response

def test_login_cookie_tokens_and_reload(env):
    response=login(env)
    assert 'HttpOnly' in response.headers['set-cookie']
    assert 'SameSite=lax' in response.headers['set-cookie']
    assert response.headers['cache-control']=='no-store'
    assert 'access-test' not in response.text and 'refresh-test' not in response.text
    assert 'access-test' not in env.store.rows[0]['token_ciphertext']
    assert not any(path=='logout' for _,path,_,_ in env.calls)
    restored=env.client.get('/api/auth/session')
    assert restored.status_code==200
    assert restored.json()['csrf_token']==response.json()['csrf_token']

@pytest.mark.parametrize('origin',[None,'https://evil.example'])
def test_login_rejects_missing_or_foreign_origin(env,origin):
    response=env.client.post('/api/auth/login',headers={'Origin':origin} if origin else {},json={'email':'a@b.test','password':'password'})
    assert response.status_code==403 and not env.calls

def test_short_existing_password_is_not_blocked_by_signup_rules(env):
    result=env.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':'a@b.test','password':'1234'})
    assert result.status_code==200

def test_unverified_identity_cannot_create_session(env,monkeypatch):
    monkeypatch.setattr(auth,'auth_request',lambda method,path,*a,**k: {'access_token':'a','refresh_token':'r'} if path=='token' else {'id':UID})
    response=env.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':'a@b.test','password':'password'})
    assert response.status_code==403 and not env.store.rows

def test_signup_metadata_and_pkce(env):
    response=env.client.post('/api/auth/signup',headers={'Origin':ORIGIN},json={
        'email':'teacher@example.test','password':'password123','full_name':'Teacher',
        'account_type':'teacher','role':'super_admin','institution_id':'fake'})
    assert response.status_code==200 and response.json()['confirmation_required']
    _,_,payload,params=env.calls[-1]
    assert payload['data']['account_type']=='teacher'
    assert 'role' not in payload['data'] and 'institution_id' not in payload['data']
    assert payload['code_challenge_method']=='s256'
    assert params['redirect_to'].startswith(ORIGIN+'/api/auth/callback?state=')
    assert 'HttpOnly' in response.headers['set-cookie']
    assert payload['code_challenge'] not in response.text

def test_secret_validation_never_echoes_password(env):
    secret='X'*300
    response=env.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':'invalid','password':secret})
    assert response.status_code==422 and secret not in response.text

def test_missing_configuration_fails_before_auth_call(env):
    env.settings.supabase_service_role_key=''
    result=env.client.post('/api/auth/login',headers={'Origin':ORIGIN},json={'email':'a@b.test','password':'password'})
    assert result.status_code==503 and not env.calls

def flow_state(env):
    response=env.client.post('/api/auth/google/start',headers={'Origin':ORIGIN})
    assert response.status_code==200
    redirect=parse_qs(urlparse(response.json()['url']).query)['redirect_to'][0]
    return parse_qs(urlparse(redirect).query)['state'][0]

def test_pkce_callback_preserves_verifier_and_creates_cookie(env):
    state=flow_state(env)
    encrypted=env.client.cookies.get(auth.FLOW_COOKIE)
    verifier,_=sessions.decrypt_tokens(encrypted)
    response=env.client.get('/api/auth/callback',params={'state':state,'code':'auth-code'},follow_redirects=False)
    assert response.status_code==303 and response.headers['location']==ORIGIN+'/'
    exchange=[call for call in env.calls if call[1]=='token'][0]
    assert exchange[2]=={'auth_code':'auth-code','code_verifier':verifier}
    assert env.client.cookies.get('sisu_session')
    assert not env.client.cookies.get(auth.FLOW_COOKIE)
    assert len(env.store.rows)==1
    # Callback replay no longer has a verifier cookie.
    again=env.client.get('/api/auth/callback',params={'state':state,'code':'auth-code'},follow_redirects=False)
    assert 'auth_error' in again.headers['location'] and len(env.store.rows)==1

@pytest.mark.parametrize('fault',['missing','mismatch','tampered','expired'])
def test_callback_fails_closed(env,fault):
    state=flow_state(env)
    if fault=='missing': env.client.cookies.clear()
    if fault=='mismatch': state='different-state'
    if fault in {'tampered','expired'}:
        value='tampered' if fault=='tampered' else sessions.encrypt_tokens('verifier',json.dumps({'state':state,'purpose':'google','expires':0}))
        env.client.cookies.clear()
        env.client.cookies.set(auth.FLOW_COOKIE,value,path='/api/auth')
    response=env.client.get('/api/auth/callback',params={'state':state,'code':'code'},follow_redirects=False)
    assert response.status_code==303 and 'auth_error' in response.headers['location']
    assert not env.store.rows and not env.calls

def test_logout_requires_csrf_then_revokes_and_is_idempotent(env):
    csrf=login(env).json()['csrf_token']
    assert env.client.delete('/api/auth/session',headers={'Origin':ORIGIN}).status_code==403
    result=env.client.delete('/api/auth/session',headers={'Origin':ORIGIN,'X-CSRF-Token':csrf})
    assert result.status_code==204 and env.store.rows[0]['revoked_at']
    assert env.store.rows[0]['token_ciphertext']=='revoked'
    assert env.client.get('/api/auth/session').status_code==401
    assert env.client.delete('/api/auth/session',headers={'Origin':ORIGIN}).status_code==204

def test_logout_keeps_browser_cookie_when_store_unavailable(env,monkeypatch):
    csrf=login(env).json()['csrf_token']
    monkeypatch.setattr(auth,'revoke_session',lambda *a: (_ for _ in ()).throw(HTTPException(503,'Unavailable')))
    response=env.client.delete('/api/auth/session',headers={'Origin':ORIGIN,'X-CSRF-Token':csrf})
    assert response.status_code==503 and env.client.cookies.get('sisu_session')

def test_expired_cookie_logout_still_succeeds(env):
    login(env)
    env.store.rows[0]['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
    assert env.client.delete('/api/auth/session',headers={'Origin':ORIGIN}).status_code==204

def test_password_update_rejects_csrf_and_revokes_sessions(env):
    csrf=login(env).json()['csrf_token']
    login(env)
    csrf=env.client.get('/api/auth/session').json()['csrf_token']
    assert env.client.put('/api/auth/password',headers={'Origin':ORIGIN},json={'password':'new-password'}).status_code==403
    response=env.client.put('/api/auth/password',headers={'Origin':ORIGIN,'X-CSRF-Token':csrf},json={'password':'new-password'})
    assert response.status_code==200 and all(r['revoked_at'] for r in env.store.rows)

def test_pending_account_cannot_read_business_data(env):
    login(env);env.profile['account_status']='pending';env.profile['role']=None
    assert env.client.get('/api/auth/session').status_code==200
    assert env.client.get('/api/courses').status_code==403

def test_student_cannot_approve_providers(env):
    csrf=login(env).json()['csrf_token']
    result=env.client.post('/api/applications/'+UID+'/review',headers={'Origin':ORIGIN,'X-CSRF-Token':csrf},json={'decision':'approved','institution_id':UID})
    assert result.status_code==403

def test_refresh_serializes_rotation_and_does_not_revoke_on_outage(env,monkeypatch):
    import psycopg
    login(env)
    raw=env.client.cookies.get('sisu_session')
    snapshot=sessions.load_session(raw)
    row=env.store.rows[0]
    lock=threading.Lock();refreshes=[]
    class Connection:
        def __enter__(self): lock.acquire();return self
        def __exit__(self,*args): lock.release()
        def execute(self,sql,args):
            if sql.startswith('select'):
                return SimpleNamespace(fetchone=lambda:(row['token_ciphertext'],row['revoked_at'],snapshot.expires_at))
            if 'revoked_at=now()' in sql: row['revoked_at']='revoked'
            else: row['token_ciphertext']=args[0]
    monkeypatch.setattr(psycopg,'connect',lambda *a,**k:Connection())
    def transport(method,path,body=None,token=None,params=None):
        if path=='user':
            if token=='access-new': return {'id':UID,'email':'a@b.test'}
            raise HTTPException(401,'Expired')
        refreshes.append(1)
        return {'access_token':'access-new','refresh_token':'refresh-new'}
    monkeypatch.setattr(sessions,'auth_request',transport)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:sessions.refresh_and_validate(snapshot),range(2)))
    assert len(refreshes)==1 and all(token=='access-new' for _,token in results)
    assert not row['revoked_at']
    monkeypatch.setattr(sessions,'auth_request',lambda *a,**k:(_ for _ in ()).throw(HTTPException(503,'Outage')))
    with pytest.raises(HTTPException) as exc: sessions.refresh_and_validate(snapshot)
    assert exc.value.status_code==503 and not row['revoked_at']

def test_production_requires_secure_cookie(env):
    env.settings.frontend_url=env.settings.public_api_url='https://sisu.example'
    with pytest.raises(RuntimeError): env.settings.require_auth()
    env.settings.session_cookie_secure=True
    env.settings.require_auth()

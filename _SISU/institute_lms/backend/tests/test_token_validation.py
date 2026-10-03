"""Access tokens must belong to this Supabase project and its Auth audience."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.config import Settings
from app import token_validation


PROJECT_REF = "yfdettlsvgsslzjjhoxo"
PROJECT_URL = f"https://{PROJECT_REF}.supabase.co"
KEY_ID = "test-signing-key"


@pytest.fixture
def signing(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(token_validation, "_jwks_client", lambda url: SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key(), key_id=KEY_ID)
    ))
    settings = Settings(
        SUPABASE_PROJECT_REF=PROJECT_REF,
        SUPABASE_URL=PROJECT_URL,
        SUPABASE_PUBLISHABLE_KEY="public-key",
    )
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "10000000-0000-0000-0000-000000000001",
        "iss": PROJECT_URL + "/auth/v1",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return key, settings, claims


def test_valid_es256_access_token(signing):
    key, settings, claims = signing
    token = jwt.encode(claims, key, algorithm="ES256", headers={"kid": KEY_ID})
    assert token_validation.validate_access_token(token, settings)["sub"] == claims["sub"]


def test_future_issued_at_reports_clock_issue_without_accepting_token(signing):
    key, settings, claims = signing
    token = jwt.encode(
        {**claims, "iat": datetime.now(timezone.utc) + timedelta(minutes=10)},
        key, algorithm="ES256", headers={"kid": KEY_ID},
    )
    diagnostics = token_validation.safe_token_diagnostics(token, settings)
    assert diagnostics["iat_seconds_ahead"] > 500
    assert token not in repr(diagnostics)
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401
    assert error.value.detail["code"] == "session_not_yet_valid"
    assert "UTC clock" in error.value.detail["message"]


def test_future_not_before_reports_clock_issue_without_accepting_token(signing):
    key, settings, claims = signing
    token = jwt.encode(
        {**claims, "nbf": datetime.now(timezone.utc) + timedelta(minutes=10)},
        key, algorithm="ES256", headers={"kid": KEY_ID},
    )
    diagnostics = token_validation.safe_token_diagnostics(token, settings)
    assert diagnostics["nbf_seconds_ahead"] > 500
    assert token not in repr(diagnostics)
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401
    assert error.value.detail["code"] == "session_not_yet_valid"
    assert "UTC clock" in error.value.detail["message"]


@pytest.mark.parametrize("change", [
    {"iss": "https://other.supabase.co/auth/v1"},
    {"aud": "anon"},
    {"role": "service_role"},
    {"exp": datetime(2020, 1, 1, tzinfo=timezone.utc)},
])
def test_wrong_issuer_audience_role_or_expiry_is_401(signing, change):
    key, settings, claims = signing
    token = jwt.encode({**claims, **change}, key, algorithm="ES256", headers={"kid": KEY_ID})
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401


def test_invalid_signature_is_401(signing):
    _, settings, claims = signing
    token = jwt.encode(
        claims,
        ec.generate_private_key(ec.SECP256R1()),
        algorithm="ES256",
        headers={"kid": KEY_ID},
    )
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401


def test_missing_key_id_is_rejected(signing):
    key, settings, claims = signing
    token = jwt.encode(claims, key, algorithm="ES256")
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401


def test_symmetric_algorithm_is_rejected_before_jwks_lookup(signing):
    _, settings, claims = signing
    token = jwt.encode(
        claims,
        "unit-test-only-not-a-real-secret-key",
        algorithm="HS256",
        headers={"kid": KEY_ID},
    )
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401


def test_key_id_must_match_the_jwks_key(signing):
    key, settings, claims = signing
    token = jwt.encode(claims, key, algorithm="ES256", headers={"kid": "different-key"})
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401


def test_subject_must_be_uuid(signing):
    key, settings, claims = signing
    token = jwt.encode(
        {**claims, "sub": "not-a-uuid"}, key, algorithm="ES256", headers={"kid": KEY_ID}
    )
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401


def test_safe_diagnostics_never_include_token_or_subject(signing):
    key, settings, claims = signing
    token = jwt.encode(claims, key, algorithm="ES256", headers={"kid": KEY_ID})
    diagnostics = token_validation.safe_token_diagnostics(token, settings)
    rendered = repr(diagnostics)
    assert token not in rendered
    assert claims["sub"] not in rendered
    assert diagnostics["algorithm"] == "ES256"
    assert diagnostics["key_id"] == KEY_ID
    assert diagnostics["issuer_matches"] is True
    assert diagnostics["audience_matches"] is True
    assert diagnostics["subject_is_uuid"] is True
    assert diagnostics["is_expired"] is False


def test_stale_jwks_client_is_rebuilt_once(monkeypatch):
    expected = SimpleNamespace(key="public-key", key_id=KEY_ID)

    class StaleClient:
        def get_signing_key_from_jwt(self, token):
            raise token_validation.PyJWKClientError("key not found")

    class FreshClient:
        def get_signing_key_from_jwt(self, token):
            return expected

    clients = iter((StaleClient(), FreshClient()))
    cache_cleared = []

    def client_factory(url):
        return next(clients)

    client_factory.cache_clear = lambda: cache_cleared.append(True)
    monkeypatch.setattr(token_validation, "_jwks_client", client_factory)

    assert token_validation._signing_key("header.payload.signature", "https://example/jwks") is expected
    assert cache_cleared == [True]


def test_project_url_must_match_project_ref():
    settings = Settings(
        SUPABASE_PROJECT_REF=PROJECT_REF,
        SUPABASE_URL="https://zyxwvutsrqponmlkjihg.supabase.co",
        SUPABASE_PUBLISHABLE_KEY="public-key",
    )
    with pytest.raises(RuntimeError, match="does not match"):
        settings.require_auth()


def test_project_ref_must_be_the_sisu_project():
    settings = Settings(
        SUPABASE_PROJECT_REF="abcdefghijklmnopqrst",
        SUPABASE_URL="https://abcdefghijklmnopqrst.supabase.co",
        SUPABASE_PUBLISHABLE_KEY="public-key",
    )

    with pytest.raises(RuntimeError, match="SISU Supabase project"):
        settings.require_auth()

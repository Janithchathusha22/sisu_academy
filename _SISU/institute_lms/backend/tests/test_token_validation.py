"""Access tokens must belong to this Supabase project and its Auth audience."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from app.config import Settings
from app import token_validation


@pytest.fixture
def signing(monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(token_validation, "_jwks_client", lambda url: SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())
    ))
    settings = Settings(SUPABASE_URL="https://project.supabase.co", SUPABASE_PUBLISHABLE_KEY="public-key")
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "10000000-0000-0000-0000-000000000001",
        "iss": "https://project.supabase.co/auth/v1",
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return key, settings, claims


def test_valid_es256_access_token(signing):
    key, settings, claims = signing
    token = jwt.encode(claims, key, algorithm="ES256")
    assert token_validation.validate_access_token(token, settings)["sub"] == claims["sub"]


@pytest.mark.parametrize("change", [
    {"iss": "https://other.supabase.co/auth/v1"},
    {"aud": "anon"},
    {"role": "service_role"},
    {"exp": datetime(2020, 1, 1, tzinfo=timezone.utc)},
])
def test_wrong_issuer_audience_role_or_expiry_is_401(signing, change):
    key, settings, claims = signing
    token = jwt.encode({**claims, **change}, key, algorithm="ES256")
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401


def test_invalid_signature_is_401(signing):
    _, settings, claims = signing
    token = jwt.encode(claims, ec.generate_private_key(ec.SECP256R1()), algorithm="ES256")
    with pytest.raises(HTTPException) as error:
        token_validation.validate_access_token(token, settings)
    assert error.value.status_code == 401

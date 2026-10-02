"""Validate Supabase access JWTs against this project's public signing keys."""

from functools import lru_cache

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError
from fastapi import HTTPException

from .config import Settings


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)


def validate_access_token(token: str, settings: Settings) -> dict:
    issuer = settings.supabase_url.rstrip("/") + "/auth/v1"
    try:
        key = _jwks_client(issuer + "/.well-known/jwks.json").get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
        if claims.get("role") != "authenticated":
            raise jwt.InvalidTokenError("Not an authenticated access token")
        return claims
    except PyJWKClientConnectionError as exc:
        raise HTTPException(503, "Supabase token verification service is unavailable") from exc
    except (PyJWTError, ValueError) as exc:
        raise HTTPException(401, "Invalid or expired token") from exc

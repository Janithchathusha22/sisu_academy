"""Validate Supabase access JWTs against this project's public signing keys."""

from datetime import datetime, timezone
from functools import lru_cache
import logging
from urllib.parse import urlparse
from uuid import UUID

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidTokenError,
    ImmatureSignatureError,
    PyJWKClientConnectionError,
    PyJWKClientError,
    PyJWTError,
)
from .config import Settings
from .errors import public_error


logger = logging.getLogger("sisu.auth")
ALLOWED_ALGORITHMS = frozenset({"ES256", "RS256"})


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    # Supabase Edge already caches JWKS for ten minutes. Keep the application
    # cache shorter and allow an explicit purge when a signing key changes.
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300, timeout=10)


def safe_token_diagnostics(token: str, settings: Settings) -> dict[str, object]:
    """Return allow-listed metadata only; never return the token or identity."""
    result: dict[str, object] = {
        "project_host": urlparse(settings.supabase_url).hostname,
        "jwks_url": settings.supabase_jwks_url,
        "token_shape_valid": token.count(".") == 2,
    }
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
        audience = claims.get("aud")
        expires = claims.get("exp")
        issued = claims.get("iat")
        not_before = claims.get("nbf")
        server_now = datetime.now(timezone.utc)
        try:
            UUID(str(claims.get("sub")))
            subject_is_uuid = True
        except (ValueError, TypeError, AttributeError):
            subject_is_uuid = False
        result.update({
            "algorithm": header.get("alg"),
            "key_id": header.get("kid"),
            "issuer_matches": claims.get("iss") == settings.supabase_issuer,
            "audience_matches": audience == "authenticated" or (
                isinstance(audience, list) and "authenticated" in audience
            ),
            "subject_is_uuid": subject_is_uuid,
            "role_matches": claims.get("role") == "authenticated",
            "expires_at": (
                datetime.fromtimestamp(expires, timezone.utc).isoformat()
                if isinstance(expires, (int, float)) else None
            ),
            "is_expired": (
                not isinstance(expires, (int, float))
                or expires <= server_now.timestamp()
            ),
            "server_utc": server_now.isoformat(),
            "iat_seconds_ahead": round(issued - server_now.timestamp()) if isinstance(issued, (int, float)) else None,
            "nbf_seconds_ahead": round(not_before - server_now.timestamp()) if isinstance(not_before, (int, float)) else None,
        })
    except (PyJWTError, ValueError, TypeError):
        result["metadata_readable"] = False
    return result


def _log_rejection(token: str, settings: Settings, exc: Exception) -> None:
    logger.warning(
        "Supabase access token rejected: error_type=%s diagnostics=%s",
        type(exc).__name__,
        safe_token_diagnostics(token, settings),
    )


def _signing_key(token: str, jwks_url: str):
    try:
        return _jwks_client(jwks_url).get_signing_key_from_jwt(token)
    except PyJWKClientConnectionError:
        raise
    except PyJWKClientError:
        # Retry once with a newly constructed client. This fixes a process that
        # retained a pre-rotation JWKS without weakening signature validation.
        _jwks_client.cache_clear()
        return _jwks_client(jwks_url).get_signing_key_from_jwt(token)


def validate_access_token(token: str, settings: Settings) -> dict:
    settings.require_auth()
    try:
        header = jwt.get_unverified_header(token)
        algorithm = header.get("alg")
        key_id = header.get("kid")
        if algorithm not in ALLOWED_ALGORITHMS:
            raise InvalidTokenError("Unsupported signing algorithm")
        if not isinstance(key_id, str) or not key_id:
            raise InvalidTokenError("Missing signing key identifier")

        key = _signing_key(token, settings.supabase_jwks_url)
        if key.key_id != key_id:
            raise InvalidTokenError("Signing key identifier mismatch")
        claims = jwt.decode(
            token,
            key.key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=settings.supabase_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
        try:
            UUID(str(claims["sub"]))
        except (ValueError, TypeError, AttributeError) as exc:
            raise InvalidTokenError("Subject must be a UUID") from exc
        if claims.get("role") != "authenticated":
            raise InvalidTokenError("Not an authenticated access token")
        return claims
    except PyJWKClientConnectionError as exc:
        _log_rejection(token, settings, exc)
        raise public_error(503, "token_verification_unavailable", "Session verification is temporarily unavailable.") from exc
    except ExpiredSignatureError as exc:
        _log_rejection(token, settings, exc)
        raise public_error(401, "session_expired", "Your session has expired. Please sign in again.") from exc
    except InvalidIssuerError as exc:
        _log_rejection(token, settings, exc)
        raise public_error(401, "session_project_mismatch", "This session belongs to a different project.") from exc
    except InvalidAudienceError as exc:
        _log_rejection(token, settings, exc)
        raise public_error(401, "session_invalid", "The sign-in session is invalid.") from exc
    except ImmatureSignatureError as exc:
        _log_rejection(token, settings, exc)
        diagnostics = safe_token_diagnostics(token, settings)
        skew_seconds = max(
            int(diagnostics.get("iat_seconds_ahead") or 0),
            int(diagnostics.get("nbf_seconds_ahead") or 0),
            0,
        )
        raise public_error(
            401,
            "session_not_yet_valid",
            "This session is not valid yet. Correct the application host's UTC clock.",
            clock_skew_seconds=skew_seconds,
        ) from exc
    except (PyJWTError, ValueError) as exc:
        _log_rejection(token, settings, exc)
        raise public_error(401, "session_invalid", "The sign-in session is invalid.") from exc

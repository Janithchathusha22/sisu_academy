"""Stable, public error payloads for authentication and connected UI failures."""

from fastapi import HTTPException


def public_error(status_code: int, code: str, message: str, **context: object) -> HTTPException:
    """Return an allow-listed error shape without leaking provider exceptions."""
    return HTTPException(status_code, {"code": code, "message": message, **context})

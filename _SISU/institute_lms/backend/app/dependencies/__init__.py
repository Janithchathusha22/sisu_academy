"""FastAPI authentication dependencies for both retained API generations."""

from dataclasses import dataclass
import secrets

from fastapi import Depends, Header, HTTPException, Request

from ..config import get_settings
from ..database import user_client
from ..auth_transport import auth_request
from ..identity_context import load_identity
from ..sessions import digest, load_session, refresh_and_validate
from .auth import Membership, Principal as BearerPrincipal, get_current_user


@dataclass
class Principal:
	id: str
	email: str | None
	role: str | None
	institution_id: str | None
	token: str
	session_id: str
	account_status: str


def current_user(
	request: Request,
	authorization: str | None = Header(default=None),
	x_csrf_token: str | None = Header(default=None),
) -> Principal:
	settings = get_settings()
	if authorization:
		scheme, separator, token = authorization.partition(" ")
		if scheme.lower() != "bearer" or not separator or not token.strip():
			raise HTTPException(401, "Bearer token required")
		token = token.strip()
		auth_user = auth_request("GET", "user", token=token)
		user_id = auth_user.get("id")
		if not user_id:
			raise HTTPException(401, "Invalid or expired token")
		profile = load_identity(user_client(token), str(user_id))
		if not profile:
			raise HTTPException(403, "Profile not provisioned")
		return Principal(
			str(user_id), auth_user.get("email"), profile.get("role"),
			profile.get("institution_id"), token, "", profile.get("account_status", "pending"),
		)

	# Retain the existing opaque-cookie flow for old same-origin clients during migration.
	raw_id = request.cookies.get(settings.session_cookie_name)
	session = load_session(raw_id)
	if request.method not in {"GET", "HEAD", "OPTIONS"}:
		if request.headers.get("origin") != settings.frontend_url.rstrip("/"):
			raise HTTPException(403, "Untrusted request origin")
		if not x_csrf_token or not secrets.compare_digest(digest(x_csrf_token), session.csrf_hash):
			raise HTTPException(403, "Invalid CSRF token")
	auth_user, token = refresh_and_validate(session)
	profile = load_identity(user_client(token), str(auth_user.id))
	if not profile:
		raise HTTPException(403, "Profile not provisioned")
	return Principal(
		str(auth_user.id), auth_user.email, profile.get("role"), profile.get("institution_id"),
		token, session.raw_id, profile.get("account_status", "pending"),
	)


def active_user(user: Principal = Depends(current_user)) -> Principal:
	if user.account_status != "active" or not user.role:
		raise HTTPException(403, "Account approval required")
	return user


def require_roles(*roles: str):
	def check(user: Principal = Depends(active_user)) -> Principal:
		if user.role not in roles:
			raise HTTPException(403, "Insufficient permissions")
		return user
	return check


__all__ = ["BearerPrincipal", "Membership", "Principal", "active_user", "current_user", "get_current_user", "require_roles"]

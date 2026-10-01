"""FastAPI authentication dependencies for both retained API generations."""

from dataclasses import dataclass
import secrets

from fastapi import Depends, Header, HTTPException, Request

from ..config import get_settings
from ..database import user_client
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


def current_user(request: Request, x_csrf_token: str | None = Header(default=None)) -> Principal:
	settings = get_settings()
	raw_id = request.cookies.get(settings.session_cookie_name)
	session = load_session(raw_id)
	if request.method not in {"GET", "HEAD", "OPTIONS"}:
		if request.headers.get("origin") != settings.frontend_url.rstrip("/"):
			raise HTTPException(403, "Untrusted request origin")
		if not x_csrf_token or not secrets.compare_digest(digest(x_csrf_token), session.csrf_hash):
			raise HTTPException(403, "Invalid CSRF token")
	auth_user, token = refresh_and_validate(session)
	client = user_client(token)
	rows = client.table("profiles").select("role,institution_id,account_status").eq("id", str(auth_user.id)).limit(1).execute().data
	if not rows:
		raise HTTPException(403, "Profile not provisioned")
	row = rows[0]
	return Principal(
		str(auth_user.id), auth_user.email, row.get("role"), row.get("institution_id"),
		token, session.raw_id, row.get("account_status", "active"),
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

from dataclasses import dataclass
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import AuthApiError
from .database import user_client

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    id: str
    email: str | None
    role: str
    institution_id: str | None
    token: str


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Bearer token required")
    token = credentials.credentials
    try:
        client = user_client(token)
        auth_user = client.auth.get_user(token).user
        if not auth_user:
            raise ValueError("No user")
        rows = client.table("profiles").select("role,institution_id").eq("id", str(auth_user.id)).limit(1).execute().data
        if not rows:
            raise HTTPException(403, "Profile not provisioned")
        return Principal(str(auth_user.id), auth_user.email, rows[0]["role"], rows[0]["institution_id"], token)
    except HTTPException:
        raise
    except (AuthApiError, ValueError):
        raise HTTPException(401, "Invalid or expired token") from None


def require_roles(*roles: str):
    def check(user: Principal = Depends(current_user)) -> Principal:
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return check

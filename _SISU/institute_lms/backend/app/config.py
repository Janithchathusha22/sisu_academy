from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY"),
    )
    supabase_database_url: str = ""
    frontend_url: str = "http://127.0.0.1:5178"
    public_api_url: str = "http://127.0.0.1:5178"
    cors_origins: str = "http://127.0.0.1:5178,http://localhost:5178"
    environment: str = "development"
    session_secret: str = ""
    session_cookie_name: str = "sisu_session"
    session_cookie_secure: bool = False
    session_max_age_seconds: int = 60 * 60 * 24 * 7
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def supabase_secret_key(self) -> str:
        return self.supabase_service_role_key

    @property
    def allowed_origins(self) -> list[str]:
        origins = {self.frontend_url.rstrip("/")}
        origins.update(item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip())
        return sorted(origins)

    def validate_runtime(self) -> None:
        if self.supabase_publishable_key and self.supabase_publishable_key == self.supabase_service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY must differ from SUPABASE_PUBLISHABLE_KEY")
        if self.environment == "production" and self.frontend_url.startswith("http://"):
            raise ValueError("FRONTEND_URL must use HTTPS in production")

    def require_auth(self) -> None:
        missing = [name for name, value in {
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_PUBLISHABLE_KEY": self.supabase_publishable_key,
            "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            "SUPABASE_DATABASE_URL": self.supabase_database_url,
            "SESSION_SECRET": self.session_secret,
        }.items() if not value]
        if missing:
            raise RuntimeError("Missing server configuration: " + ", ".join(missing))
        if len(self.session_secret) < 32:
            raise RuntimeError("SESSION_SECRET must contain at least 32 characters")
        if not self.supabase_url.startswith("https://"):
            raise RuntimeError("SUPABASE_URL must be HTTPS")
        if self.public_api_url.rstrip("/") != self.frontend_url.rstrip("/"):
            raise RuntimeError("Use a same-origin /api proxy; PUBLIC_API_URL must match FRONTEND_URL")
        if urlparse(self.frontend_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
            if not self.session_cookie_secure or not self.frontend_url.startswith("https://"):
                raise RuntimeError("Production requires HTTPS and secure cookies")


@lru_cache
def get_settings() -> Settings:
    return Settings()
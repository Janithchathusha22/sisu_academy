from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import urlparse

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


EXPECTED_SUPABASE_PROJECT_REF = "yfdettlsvgsslzjjhoxo"


class Settings(BaseSettings):
    supabase_project_ref: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_PROJECT_REF", "VITE_SUPABASE_PROJECT_REF"),
    )
    supabase_url: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_URL", "VITE_SUPABASE_URL"),
    )
    supabase_publishable_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_PUBLISHABLE_KEY", "VITE_SUPABASE_PUBLISHABLE_KEY"),
    )
    supabase_database_url: str = ""
    frontend_url: str = "http://127.0.0.1:5178"
    cors_origins: str = "http://127.0.0.1:5178,http://localhost:5178"
    environment: str = "development"
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        origins = {self.frontend_url.rstrip("/")}
        origins.update(item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip())
        return sorted(origins)

    @property
    def supabase_issuer(self) -> str:
        return self.supabase_url.rstrip("/") + "/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return self.supabase_issuer + "/.well-known/jwks.json"

    def validate_runtime(self) -> None:
        if self.environment == "production" and self.frontend_url.startswith("http://"):
            raise ValueError("FRONTEND_URL must use HTTPS in production")

    def require_auth(self) -> None:
        missing = [name for name, value in {
            "SUPABASE_PROJECT_REF": self.supabase_project_ref,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_PUBLISHABLE_KEY": self.supabase_publishable_key,
        }.items() if not value]
        if missing:
            raise RuntimeError("Missing server configuration: " + ", ".join(missing))
        if not re.fullmatch(r"[a-z0-9]{20}", self.supabase_project_ref):
            raise RuntimeError("SUPABASE_PROJECT_REF is invalid")
        if self.supabase_project_ref != EXPECTED_SUPABASE_PROJECT_REF:
            raise RuntimeError("SUPABASE_PROJECT_REF does not identify the SISU Supabase project")
        parsed = urlparse(self.supabase_url)
        local = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
        if parsed.scheme != "https" and not local:
            raise RuntimeError("SUPABASE_URL must use HTTPS except for local development")
        if not local and parsed.hostname != f"{self.supabase_project_ref}.supabase.co":
            raise RuntimeError("SUPABASE_URL does not match SUPABASE_PROJECT_REF")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise RuntimeError("SUPABASE_URL must be the project origin without a path")


@lru_cache
def get_settings() -> Settings:
    return Settings()

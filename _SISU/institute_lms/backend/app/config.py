from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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

    def validate_runtime(self) -> None:
        if self.environment == "production" and self.frontend_url.startswith("http://"):
            raise ValueError("FRONTEND_URL must use HTTPS in production")

    def require_auth(self) -> None:
        missing = [name for name, value in {
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_PUBLISHABLE_KEY": self.supabase_publishable_key,
        }.items() if not value]
        if missing:
            raise RuntimeError("Missing server configuration: " + ", ".join(missing))
        if not self.supabase_url.startswith(("https://", "http://127.0.0.1:", "http://localhost:")):
            raise RuntimeError("SUPABASE_URL must use HTTPS except for local development")


@lru_cache
def get_settings() -> Settings:
    return Settings()

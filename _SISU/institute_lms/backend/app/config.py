"""Runtime configuration loaded only on application startup."""

from functools import lru_cache

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: AnyHttpUrl
    supabase_publishable_key: str = Field(min_length=8)
    supabase_secret_key: str = Field(min_length=8)
    frontend_url: AnyHttpUrl = "http://127.0.0.1:5178"
    cors_origins: str = "http://127.0.0.1:5178,http://localhost:5178"
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("supabase_publishable_key", "supabase_secret_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        value = value.strip()
        if any(character.isspace() for character in value):
            raise ValueError("Supabase keys cannot contain whitespace")
        return value

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"development", "test", "staging", "production"}:
            raise ValueError("ENVIRONMENT must be development, test, staging, or production")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        origins = {str(self.frontend_url).rstrip("/")}
        origins.update(item.strip().rstrip("/") for item in self.cors_origins.split(",") if item.strip())
        return sorted(origins)

    def validate_runtime(self) -> None:
        if self.supabase_publishable_key == self.supabase_secret_key:
            raise ValueError("SUPABASE_SECRET_KEY must differ from SUPABASE_PUBLISHABLE_KEY")
        if self.environment == "production" and str(self.frontend_url).startswith("http://"):
            raise ValueError("FRONTEND_URL must use HTTPS in production")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    settings.validate_runtime()
    return settings

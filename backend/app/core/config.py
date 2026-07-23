from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PTT Alert Hub"
    environment: str = "development"
    timezone: str = Field(
        default="Asia/Taipei",
        validation_alias=AliasChoices("TIMEZONE", "TZ"),
    )

    admin_username: str = "admin"
    admin_password: str = "change-me-now"
    jwt_secret: str = "replace-with-a-long-random-secret"
    jwt_expire_minutes: int = 1440

    database_url: str = "sqlite:///./data/ptt_alert_hub.db"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value

        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    ptt_base_url: str = "https://www.ptt.cc"
    ptt_request_delay_seconds: float = 2.0
    ptt_timeout_seconds: float = 15.0
    crawl_lock_ttl_seconds: int = 1800

    worker_sync_seconds: int = 10
    worker_lease_ttl_seconds: int = 30
    worker_heartbeat_timeout_seconds: int = 45

    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def telegram_configured(self) -> bool:
        return bool(self.telegram_bot_token.strip() and self.telegram_chat_id.strip())

    def ensure_local_data_directory(self) -> None:
        sqlite_prefix = "sqlite:///"
        if not self.database_url.startswith(sqlite_prefix):
            return

        raw_path = self.database_url.removeprefix(sqlite_prefix)
        if raw_path == ":memory:":
            return

        database_path = (
            Path(f"/{raw_path}")
            if self.database_url.startswith("sqlite:////")
            else Path(raw_path)
        )
        database_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_local_data_directory()
    return settings

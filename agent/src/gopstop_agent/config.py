"""Environment-backed service configuration."""

from pathlib import Path

from pydantic import AliasChoices, Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
    )

    valkey_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("AGENT_VALKEY_URL", "SPRING_DATA_REDIS_URL"),
        description="Redis-compatible Valkey connection URL.",
    )
    session_ttl_seconds: int = Field(default=60 * 60 * 24, ge=60, le=60 * 60 * 24 * 30)
    session_max_messages: int = Field(default=200, ge=2, le=10_000, multiple_of=2)

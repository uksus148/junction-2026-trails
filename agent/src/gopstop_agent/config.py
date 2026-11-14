"""Environment-backed service configuration."""

from pathlib import Path

from pydantic import AliasChoices, Field, HttpUrl, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AGENT_",
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
        populate_by_name=True,
    )

    valkey_url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("AGENT_VALKEY_URL", "SPRING_DATA_REDIS_URL"),
        description="Redis-compatible Valkey connection URL.",
    )
    session_ttl_seconds: int = Field(default=60 * 60 * 24, ge=60, le=60 * 60 * 24 * 30)
    session_max_messages: int = Field(default=200, ge=2, le=10_000, multiple_of=2)
    valkey_connect_timeout_seconds: float = Field(default=2, gt=0, le=30)
    valkey_socket_timeout_seconds: float = Field(default=2, gt=0, le=30)
    cors_origins: list[str] = ["http://localhost:5173"]
    anthropic_api_key: SecretStr = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    exa_api_key: SecretStr = Field(default="", validation_alias="EXA_API_KEY")
    anthropic_model: str = "claude-haiku-5-5"
    provider_timeout_seconds: float = Field(default=20, gt=0, le=60)
    discovery_timeout_seconds: float = Field(default=60, gt=0, le=180)
    api_base_url: HttpUrl = "http://localhost:8080"
    api_timeout_seconds: float = Field(default=20, gt=0, le=120)
    handoff_timeout_seconds: float = Field(default=60, gt=0, le=180)
    nominatim_base_url: HttpUrl = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = Field(
        default="trego/0.1 (https://github.com/uksus148/trego)",
        min_length=8,
    )

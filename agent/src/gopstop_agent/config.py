"""Environment-backed service configuration."""

from pathlib import Path
from typing import Literal

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
    llm_provider: Literal["anthropic", "groq"] = "anthropic"
    groq_api_key: SecretStr = Field(default="", validation_alias="GROQ_API_KEY")
    groq_model: str = "openai/gpt-oss-120b"
    provider_timeout_seconds: float = Field(default=20, gt=0, le=60)
    discovery_timeout_seconds: float = Field(default=60, gt=0, le=180)
    api_base_url: HttpUrl = "http://localhost:8080"
    chat_enabled: bool = False
    chat_timeout_seconds: float = Field(default=180, gt=0, le=300)
    api_timeout_seconds: float = Field(default=20, gt=0, le=120)
    handoff_timeout_seconds: float = Field(default=60, gt=0, le=180)
    nominatim_base_url: HttpUrl = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = Field(
        default="trego/0.1 (contact: https://github.com/uksus148/trego./issues)",
        min_length=8,
    )

    @property
    def llm_key(self) -> SecretStr:
        return self.groq_api_key if self.llm_provider == "groq" else self.anthropic_api_key

    @property
    def llm_model(self) -> str:
        return self.groq_model if self.llm_provider == "groq" else self.anthropic_model

    def require_chat_configuration(self) -> None:
        if not self.llm_key.get_secret_value().strip() or not self.llm_model.strip() or not self.exa_api_key.get_secret_value().strip():
            raise ValueError("Enabled chat requires the selected LLM key, EXA_API_KEY and a model ID.")

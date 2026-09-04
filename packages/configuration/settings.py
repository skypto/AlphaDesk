from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SystemMode(StrEnum):
    PAPER_ONLY = "PAPER_ONLY"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    mode: SystemMode = Field(
        default=SystemMode.PAPER_ONLY,
        validation_alias="ALPHADESK_MODE",
    )
    environment: str = Field(
        default="development",
        validation_alias="ALPHADESK_ENVIRONMENT",
    )
    log_level: str = Field(default="INFO", validation_alias="ALPHADESK_LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+psycopg://alphadesk:alphadesk_dev@localhost:5432/alphadesk",
        validation_alias="ALPHADESK_DATABASE_URL",
    )
    nats_url: str = Field(
        default="nats://localhost:4222",
        validation_alias="ALPHADESK_NATS_URL",
    )
    infrastructure_checks: bool = Field(
        default=False,
        validation_alias="ALPHADESK_INFRASTRUCTURE_CHECKS",
    )
    broker_reconciliation_interval_seconds: int = Field(
        default=30,
        ge=10,
        validation_alias="ALPHADESK_BROKER_RECONCILIATION_INTERVAL_SECONDS",
    )
    broker_maximum_state_age_seconds: int = Field(
        default=90,
        ge=30,
        validation_alias="ALPHADESK_BROKER_MAXIMUM_STATE_AGE_SECONDS",
    )
    llm_provider: str = Field(default="fixture", validation_alias="LLM_PROVIDER")
    ai_timeout_seconds: int = Field(
        default=20,
        ge=1,
        le=120,
        validation_alias="ALPHADESK_AI_TIMEOUT_SECONDS",
    )
    supabase_url: str | None = Field(default=None, validation_alias="SUPABASE_URL")
    supabase_secret_key: SecretStr | None = Field(
        default=None, validation_alias="SUPABASE_SECRET_KEY"
    )
    supabase_jwt_audience: str = Field(
        default="authenticated", validation_alias="SUPABASE_JWT_AUDIENCE"
    )
    admin_emails_csv: str = Field(default="", validation_alias="ALPHADESK_ADMIN_EMAILS")
    credential_master_keys: SecretStr | None = Field(
        default=None, validation_alias="ALPHADESK_CREDENTIAL_MASTER_KEYS"
    )
    demo_session_signing_key: SecretStr | None = Field(
        default=None, validation_alias="ALPHADESK_DEMO_SESSION_SIGNING_KEY"
    )
    workspace_connection_limit: int = Field(
        default=20, ge=1, le=100, validation_alias="ALPHADESK_WORKSPACE_CONNECTION_LIMIT"
    )

    @field_validator("mode", mode="before")
    @classmethod
    def reject_non_paper_mode(cls, value: object) -> object:
        if value != SystemMode.PAPER_ONLY and value != SystemMode.PAPER_ONLY.value:
            raise ValueError("AlphaDesk v1 supports PAPER_ONLY; live trading fails closed.")
        return value

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Unsupported log level: {value}")
        return normalized

    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        normalized = value.lower()
        if normalized != "fixture":
            raise ValueError(
                "Global LLM_PROVIDER must remain fixture; connected providers are BYOK"
            )
        return normalized

    @field_validator(
        "supabase_url",
        "supabase_secret_key",
        "credential_master_keys",
        "demo_session_signing_key",
        mode="before",
    )
    @classmethod
    def blank_optional_platform_values(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("supabase_secret_key")
    @classmethod
    def validate_supabase_secret_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().startswith("sb_secret_"):
            raise ValueError("SUPABASE_SECRET_KEY must be a modern server-only sb_secret_ key")
        return value

    @property
    def admin_emails(self) -> frozenset[str]:
        return frozenset(
            item.strip().lower() for item in self.admin_emails_csv.split(",") if item.strip()
        )

    @property
    def authentication_configured(self) -> bool:
        return bool(self.supabase_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar, Optional
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .enums import *

from functools import lru_cache


class Settings(BaseSettings):

    BASE_DIR: ClassVar[Path] = Path(__file__).resolve().parents[3]
    
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / "backend" / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = Field(default="DeployBridge")
    APP_VERSION: str = Field(default="0.1.0")
    APP_DESCRIPTION: str = Field(default="DevOps automation ai powered agent")
    DEBUG: bool = Field(default=False)
    ENV_TYPE: Environment = Field(default=Environment.LOCAL)

    DOCS_URL: Optional[str] = Field(default="/docs")
    REDOC_URL: Optional[str] = Field(default=None)

    
    HOST: Optional[str] = Field(default="0.0.0.0")
    PORT: Optional[int] = Field(default=8000)


    LOG_LEVEL: Optional[str] = Field(default="INFO")


    DATABASE_URL: str = Field(...)


    GITHUB_CLIENT_ID: str = Field(...)
    GITHUB_CLIENT_SECRET: str = Field(...)


    JWT_SECRET_KEY: str = Field(...)
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=10000)

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "off", "no"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "on", "yes"}:
                return True
        return value

    @field_validator("DOCS_URL", "REDOC_URL", "HOST", "LOG_LEVEL", mode="before")
    @classmethod
    def parse_blank_optional_strings(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("PORT", mode="before")
    @classmethod
    def parse_port(cls, value):
        if isinstance(value, str) and not value.strip():
            return 8000
        return value

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        if not isinstance(value, str) or "asyncpg" not in value:
            return value

        parsed = urlsplit(value)
        query_params = []

        for key, param_value in parse_qsl(parsed.query, keep_blank_values=True):
            if key == "sslmode":
                query_params.append(("ssl", param_value))
                continue
            if key == "channel_binding":
                continue
            query_params.append((key, param_value))

        return urlunsplit(parsed._replace(query=urlencode(query_params)))



@lru_cache
def get_settings() -> Settings:
    return Settings()

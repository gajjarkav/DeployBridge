from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

from .enums import *

from functools import lru_cache


class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
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



@lru_cache
def get_settings() -> Settings:
    return Settings()

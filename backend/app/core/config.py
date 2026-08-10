from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ChartVision Core"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://chartvision:chartvision@postgres:5432/chartvision"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

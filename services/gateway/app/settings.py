from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "gateway"
    summarizer_url: str = "http://summarizer:8030"
    notifier_url: str = "http://notifier:8040"
    ingestion_url: str = "http://ingestion:8020"
    app_timezone: str = "Asia/Kolkata"
    timeout_seconds: float = 10.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "ingestion"
    summarizer_url: str = "http://summarizer:8030"
    notifier_url: str = "http://notifier:8040"
    auth_url: str = "http://auth:8050"
    app_timezone: str = "Asia/Kolkata"

    ms_tenant_id: str = "common"
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_graph_scope: str = "Mail.Read User.Read offline_access"
    allow_sample_mail: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "auth"
    app_timezone: str = "Asia/Kolkata"

    ms_tenant_id: str = "common"
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_redirect_uri: str = "http://localhost:8000/api/mail/oauth/callback"
    ms_graph_scope: str = "Mail.Read User.Read offline_access"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


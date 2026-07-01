from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://scrabble:scrabble@localhost:5432/scrabble_helper"
    session_secret: str = "dev-change-me-in-production"
    google_client_id: str = ""
    google_client_secret: str = ""
    base_url: str = "http://localhost:8080"
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False
    dev_auth_bypass: bool = False
    dev_user_email: str = "dev@example.com"
    dev_user_name: str = "Dev User"
    local_auth_enabled: bool = True
    admin_email: str = ""
    admin_password: str = ""
    email_verification_enabled: bool = True
    email_verification_ttl_minutes: int = 15
    email_verification_dev_expose_code: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True


settings = Settings()

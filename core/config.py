from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Discord
    discord_bot_token: str = Field(..., alias="DISCORD_BOT_TOKEN")
    discord_client_id: str = Field(..., alias="DISCORD_CLIENT_ID")
    discord_client_secret: str = Field(..., alias="DISCORD_CLIENT_SECRET")
    discord_public_key: str = Field(
        "7ecd745ac9ae4b6f6dd475f82855caed69e88ba1aafc72e36dd066cfc013dca2",
        alias="DISCORD_PUBLIC_KEY",
    )
    discord_redirect_uri: str = Field(
        "http://localhost:8000/auth/callback", alias="DISCORD_REDIRECT_URI"
    )
    app_base_url: str = Field("http://localhost:8000", alias="APP_BASE_URL")

    # Database
    database_url: str = Field(
        "postgresql+asyncpg://ticketpulse:ticketpulse@localhost:5432/ticketpulse",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field("redis://localhost:6379", alias="REDIS_URL")

    # Email — SMTP
    email_host: str = Field("smtp.gmail.com", alias="EMAIL_HOST")
    email_port: int = Field(587, alias="EMAIL_PORT")
    email_username: str = Field("", alias="EMAIL_USERNAME")
    email_password: str = Field("", alias="EMAIL_PASSWORD")
    email_from: str = Field("TicketPulse <no-reply@ticketpulse.app>", alias="EMAIL_FROM")

    # Email — SendGrid (takes precedence over SMTP when set)
    sendgrid_api_key: str = Field("", alias="SENDGRID_API_KEY")

    # App
    app_secret_key: str = Field("change-me", alias="APP_SECRET_KEY")
    debug: bool = Field(False, alias="DEBUG")
    scraper_interval_seconds: int = Field(60, alias="SCRAPER_INTERVAL_SECONDS")


settings = Settings()

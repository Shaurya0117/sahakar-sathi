from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Security
    SECRET_KEY: str = "change-me-insecure-default-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///./cooperative.db"

    # App
    APP_ENV: str = "development"

    # Channel Integrations (WhatsApp & Voice)
    WHATSAPP_PROVIDER: str = "mock"  # "mock" | "twilio" | "telnyx"
    VOICE_PROVIDER: str = "mock"     # "mock" | "twilio"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_NUMBER: str = ""
    TWILIO_VOICE_NUMBER: str = ""
    TWILIO_WEBHOOK_SECRET: str = ""

    # Telnyx WhatsApp Integration
    TELNYX_API_KEY: str = ""
    TELNYX_WHATSAPP_NUMBER: str = ""
    TELNYX_MESSAGING_PROFILE_ID: str = ""
    TELNYX_WEBHOOK_SECRET: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()

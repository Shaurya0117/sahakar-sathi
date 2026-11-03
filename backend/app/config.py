from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Security
    SECRET_KEY: str
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

    # Proof of Completion System
    PROOF_SECRET: str = "dev-change-me-before-deploy"
    PROOF_MAX_DISTANCE_M: float = 500.0
    PROOF_NONCE_GRACE_DAYS: int = 2
    PROOF_CODE_MAX_TRIES: int = 5

    # SMS Gateway Settings (Voice Booking Dispatch)
    SMS_GATEWAY: str = "textbelt"   # "textbelt" | "android"
    TEXTBELT_KEY: str = "textbelt"  # Use "textbelt" for free tier (1/day) or a paid key
    ANDROID_GW_URL: str = ""        # Android SMS Gateway URL (production)
    ANDROID_GW_USER: str = ""
    ANDROID_GW_PASS: str = ""
    SMS_WEBHOOK_SECRET: str = ""    # Secret token for Android SMS Gateway / external provider webhooks
    SMS_REPLY_TIMEOUT_MINUTES: int = 10  # Auto-timeout for worker response before reassigning
    MAX_DISPATCH_ATTEMPTS: int = 3       # Max sequential worker offers before unassigning

    # Machine Learning Settings
    ML_ENABLED: bool = True
    ML_TIEBREAK_TOP_K: int = 3
    ML_TIEBREAK_MARGIN: float = 2.0

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.APP_ENV == "production":
            dev_defaults = {
                "change-me",
                "dev-change-me-before-deploy",
                "dev-secret-key-for-simulations",
                "test-secret-key-for-ml-tests",
                "secret",
                "",
            }
            if not self.SECRET_KEY or self.SECRET_KEY.strip() in dev_defaults:
                raise ValueError("In production, SECRET_KEY must be set to a secure, non-default value.")
            if not self.PROOF_SECRET or self.PROOF_SECRET.strip() in dev_defaults:
                raise ValueError("In production, PROOF_SECRET must be set to a secure, non-default value.")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()


"""
Global constants for platform configuration.
"""

# Worker Fatigue: Maximum allowable fatigue before assignments are blocked or excluded from matches.
MAX_FATIGUE_THRESHOLD = 80.0

# Machine Learning configuration shortcuts
ML_ENABLED = settings.ML_ENABLED
ML_TIEBREAK_TOP_K = settings.ML_TIEBREAK_TOP_K
ML_TIEBREAK_MARGIN = settings.ML_TIEBREAK_MARGIN

# Weibull Parameters per Appliance (Characteristic Life in days, Shape factor)
# assumed values, not from real data.
WEIBULL_PARAMS = {
    'Air Conditioner': {'eta': 2500, 'beta': 1.5},
    'Ceiling Fan': {'eta': 3600, 'beta': 1.2},
    'Plumbing System': {'eta': 4000, 'beta': 2.0},
    'Refrigerator': {'eta': 3000, 'beta': 1.5},
    'Washing Machine': {'eta': 2000, 'beta': 1.8},
    'Electrical Board': {'eta': 5000, 'beta': 1.1},
    'General Appliance': {'eta': 3000, 'beta': 1.5}
}

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI
    anthropic_api_key: str = ""
    google_gemini_api_key: str = ""

    # Monetisation & Cost Tracking (Paid.ai)
    paid_api_key: str = ""

    # Voice
    elevenlabs_api_key: str = ""

    # Payments
    stripe_secret_key: str = ""

    # Communication
    sendgrid_api_key: str = ""

    # Social Media — Twitter/X
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_access_token: str = ""
    twitter_access_token_secret: str = ""

    # Google Calendar + Gmail (OAuth2)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_calendar_id: str = "primary"
    google_oauth_token_json_path: str = str(Path(__file__).resolve().parent.parent / "token.json")

    # WhatsApp Cloud API (Meta)
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_business_id: str = ""
    whatsapp_api_version: str = "v21.0"

    # Web Search
    serper_api_key: str = ""

    # Visual Memory
    miro_api_token: str = ""
    miro_board_id: str = ""

    # Database — sync sqlite3 used for MVP simplicity
    database_url: str = "sqlite:///./agentflow.db"
    agentflow_db_path: str = str(Path(__file__).resolve().parent.parent / "agentflow.db")

    # App
    app_name: str = "AgentFlow"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

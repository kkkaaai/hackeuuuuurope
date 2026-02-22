from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # AI
    anthropic_api_key: str = ""
    google_gemini_api_key: str = ""

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

    # Web Search
    serper_api_key: str = ""

    # Visual Memory
    miro_api_token: str = ""
    miro_board_id: str = ""

    # Database — sync sqlite3 used for MVP simplicity
    database_url: str = "sqlite:///./agentflow.db"

    # App
    app_name: str = "AgentFlow"
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

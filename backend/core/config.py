from functools import lru_cache

from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Centralized configuration loaded from environment variables.

    All backend modules must access env vars through this class.
    Never call os.getenv() directly in application code.
    """

    model_config = ConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""

    # JWT — no fallback; app refuses to start without SECRET_KEY
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if not v:
            raise ValueError(
                "SECRET_KEY environment variable is required and must not be empty"
            )
        return v

    # Twitch OAuth
    twitch_client_id: str = ""
    twitch_client_secret: str = ""
    twitch_redirect_uri: str = "http://localhost:8000/api/v1/auth/twitch/callback"

    # Twitch content (comma-separated strings; parsed into lists by properties)
    twitch_channels: str = ""
    twitch_categories: str = "Just Chatting,Grand Theft Auto V,VALORANT,League of Legends"

    # Groq
    groq_api_key: str = ""

    # Opus Clip (optional)
    opus_clip_api_key: str = ""

    # CORS — use FRONTEND_URL to restrict allowed origins in production
    frontend_url: str = "http://localhost:3000"

    @property
    def twitch_channels_list(self) -> list[str]:
        return [ch.strip() for ch in self.twitch_channels.split(",") if ch.strip()]

    @property
    def twitch_categories_list(self) -> list[str]:
        return [c.strip() for c in self.twitch_categories.split(",") if c.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

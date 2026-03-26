"""Configuration loading for the LMS Telegram bot.

Loads secrets from .env.bot.secret using pydantic-settings.
This pattern loads secrets from environment files.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Bot directory (parent of this file)
BOT_DIR = Path(__file__).parent


class BotSettings(BaseSettings):
    """Bot configuration settings."""

    model_config = SettingsConfigDict(
        env_file=BOT_DIR / ".env.bot.secret",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram bot token
    bot_token: str = ""

    # LMS API configuration
    lms_api_base_url: str = "http://localhost:42002"
    lms_api_key: str = ""

    # LLM API configuration
    llm_api_key: str = ""
    llm_api_base_url: str = "http://localhost:42005/v1"
    llm_api_model: str = "coder-model"


def load_settings() -> BotSettings:
    """Load bot settings from environment."""
    return BotSettings()

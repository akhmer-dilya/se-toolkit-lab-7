"""Services for the LMS Telegram bot.

Services handle external API communication (LMS backend, LLM).
"""

from services.lms_api import LMSAPIClient, LMSAPIError

__all__ = ["LMSAPIClient", "LMSAPIError"]

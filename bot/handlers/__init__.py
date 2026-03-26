"""Command handlers for the LMS Telegram bot.

Handlers are plain functions that take input and return text.
They don't know about Telegram — same function works from --test,
unit tests, or Telegram. This is called *separation of concerns*.

Handlers use the LMS API client to fetch real data from the backend.
All errors are caught and returned as user-friendly messages.
"""

from typing import Any
import sys
from pathlib import Path

# Add bot directory to path for imports
BOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BOT_DIR))

from config import BotSettings
from services.lms_api import LMSAPIClient, LMSAPIError
from services.llm_client import LLMClient
from services.intent_router import route_message, get_keyboard_buttons


def _get_api_client() -> LMSAPIClient:
    """Create an API client from settings."""
    settings = BotSettings()
    return LMSAPIClient(
        base_url=settings.lms_api_base_url,
        api_key=settings.lms_api_key,
    )


def _get_llm_client() -> LLMClient:
    """Create an LLM client from settings."""
    settings = BotSettings()
    return LLMClient(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base_url,
        model=settings.llm_api_model,
    )


def handle_start() -> str:
    """Handle /start command."""
    return """Welcome! I'm your LMS assistant bot.

I can help you with:
• Viewing lab results and pass rates
• Finding top students and group comparisons
• Analyzing completion rates and timelines
• Syncing data from the autochecker

Just ask me a question in natural language, like:
• "What labs are available?"
• "Show me scores for lab 4"
• "Which lab has the lowest pass rate?"
• "Who are the top 5 students in lab 3?"

Use /help to see all available commands."""


def handle_help() -> str:
    """Handle /help command."""
    return """Available commands:
/start - Start the bot
/help - Show this help message
/health - Check backend connection
/labs - List available labs
/scores <lab> - View pass rates for a specific lab (e.g., /scores lab-04)

You can also ask questions in natural language:
• "What labs are available?"
• "Show me scores for lab 4"
• "Which lab has the lowest pass rate?"
• "Who are the top 5 students?"
• "How many students are enrolled?"
• "Compare group A and group B in lab 3" """


def handle_health() -> str:
    """Handle /health command."""
    try:
        client = _get_api_client()
        result = client.health_check()
        return f"Backend is healthy. {result['item_count']} items available."
    except LMSAPIError as e:
        return e.message


def handle_labs() -> str:
    """Handle /labs command."""
    try:
        client = _get_api_client()
        items = client.get_items()

        # Filter for labs (type == "lab" and parent_id is None)
        labs = [item for item in items if item.get("type") == "lab" and item.get("parent_id") is None]

        if not labs:
            return "No labs available. The backend may be empty or the ETL pipeline needs to sync."

        lines = ["Available labs:"]
        for lab in labs:
            lab_title = lab.get("title", "Unknown Lab")
            lines.append(f"- {lab_title}")

        return "\n".join(lines)
    except LMSAPIError as e:
        return e.message


def handle_scores(args: str = "") -> str:
    """Handle /scores command."""
    if not args:
        return "Usage: /scores <lab> (e.g., /scores lab-04). Use /labs to see available labs."

    try:
        client = _get_api_client()

        # Get pass rates for the lab (returns a list)
        pass_rates = client.get_analytics_pass_rates(lab=args)

        if not pass_rates:
            return f"No pass rate data available for {args}. The lab may not exist or has no submissions."

        # Format the response
        lines = [f"Pass rates for {args}:"]
        for rate in pass_rates:
            task_title = rate.get("task", "Unknown Task")
            avg_score = rate.get("avg_score", 0)
            attempts = rate.get("attempts", 0)
            lines.append(f"- {task_title}: {avg_score:.1f}% ({attempts} attempts)")

        return "\n".join(lines)
    except LMSAPIError as e:
        return e.message


def handle_message(user_message: str, debug: bool = False) -> str:
    """Handle natural language messages using the intent router.
    
    This is the main entry point for natural language queries.
    The message is routed through the LLM which decides which tools to call.
    
    Args:
        user_message: The user's message text
        debug: If True, print debug info to stderr
        
    Returns:
        Response text
    """
    try:
        llm_client = _get_llm_client()
        api_client = _get_api_client()
        
        response = route_message(user_message, llm_client, api_client, debug=debug)
        return response
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            return "LLM error: HTTP 401 Unauthorized. The Qwen OAuth token may have expired. Try: cd ~/qwen-code-oai-proxy && docker compose restart"
        return f"Error processing your request: {error_msg}"


def handle_unknown() -> str:
    """Handle unknown commands."""
    return "Unknown command. Use /help to see available commands."


def get_inline_keyboard() -> list[list[dict[str, str]]]:
    """Get inline keyboard buttons for common queries.
    
    Returns:
        List of button rows for inline keyboard
    """
    return get_keyboard_buttons()

"""Command handlers for the LMS Telegram bot.

Handlers are plain functions that take input and return text.
They don't know about Telegram — same function works from --test,
unit tests, or Telegram. This is called *separation of concerns*.
"""


def handle_start() -> str:
    """Handle /start command."""
    return "Welcome! I'm your LMS assistant bot. Use /help to see available commands."


def handle_help() -> str:
    """Handle /help command."""
    return """Available commands:
/start - Start the bot
/help - Show this help message
/health - Check backend connection
/labs - List available labs
/scores - View your scores"""


def handle_health() -> str:
    """Handle /health command."""
    return "Backend status: OK (placeholder)"


def handle_labs() -> str:
    """Handle /labs command."""
    return "Available labs: Lab 01, Lab 02, Lab 03, Lab 04 (placeholder)"


def handle_scores(args: str = "") -> str:
    """Handle /scores command."""
    if args:
        return f"Scores for {args}: Not implemented yet"
    return "Your scores: Not implemented yet"


def handle_unknown() -> str:
    """Handle unknown commands."""
    return "Unknown command. Use /help to see available commands."

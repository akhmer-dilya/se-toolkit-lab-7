#!/usr/bin/env python3
"""
Telegram bot entry point with --test mode.

Usage:
    uv run bot.py --test "which lab has the lowest pass rate?"  # Test mode with natural language
    uv run bot.py --test "/start"    # Test mode with slash command
    uv run bot.py                    # Production mode (connects to Telegram)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Bot directory
BOT_DIR = Path(__file__).parent
sys.path.insert(0, str(BOT_DIR))

from handlers import (
    handle_start,
    handle_help,
    handle_health,
    handle_labs,
    handle_scores,
    handle_unknown,
    handle_message,
    get_inline_keyboard,
)
from config import load_settings

# aiogram imports
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_handler(command: str):
    """Get handler function for a command."""
    handlers = {
        "/start": handle_start,
        "/help": handle_help,
        "/health": handle_health,
        "/labs": handle_labs,
        "/scores": handle_scores,
    }
    return handlers.get(command, handle_unknown)


def run_test_mode(command: str) -> None:
    """Run bot in test mode - print response to stdout."""
    # Parse command and arguments
    text = command.strip()
    
    # Check if it's a slash command or natural language
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        handler = get_handler(cmd)

        if cmd == "/scores":
            response = handler(args)
        else:
            response = handler()
    else:
        # Natural language message - use intent router
        response = handle_message(text, debug=True)

    print(response)
    sys.exit(0)


def _build_inline_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard from button definitions."""
    keyboard_buttons = get_inline_keyboard()
    keyboard = []
    
    for row in keyboard_buttons:
        keyboard_row = []
        for btn in row:
            keyboard_row.append(InlineKeyboardButton(
                text=btn["text"],
                callback_data=btn["callback_data"],
            ))
        keyboard.append(keyboard_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def run_telegram_mode() -> None:
    """Run bot in production mode with Telegram."""
    settings = load_settings()

    if not settings.bot_token:
        logger.error("BOT_TOKEN not found in .env.bot.secret")
        sys.exit(1)

    logger.info("Starting Telegram bot...")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_start(message: types.Message) -> None:
        """Handle /start command."""
        response = handle_start()
        keyboard = _build_inline_keyboard()
        await message.answer(response, reply_markup=keyboard)

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message) -> None:
        """Handle /help command."""
        response = handle_help()
        await message.answer(response)

    @dp.message(Command("health"))
    async def cmd_health(message: types.Message) -> None:
        """Handle /health command."""
        response = handle_health()
        await message.answer(response)

    @dp.message(Command("labs"))
    async def cmd_labs(message: types.Message) -> None:
        """Handle /labs command."""
        response = handle_labs()
        await message.answer(response)

    @dp.message(Command("scores"))
    async def cmd_scores(message: types.Message) -> None:
        """Handle /scores command."""
        args = message.text.split(maxsplit=1)
        arg = args[1] if len(args) > 1 else ""
        response = handle_scores(arg)
        await message.answer(response)

    @dp.message()
    async def handle_text_message(message: types.Message) -> None:
        """Handle natural language messages using intent router."""
        user_text = message.text or ""
        
        # Show typing action while processing
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        
        # Process with intent router (debug output to stderr)
        response = handle_message(user_text, debug=True)
        await message.answer(response)

    @dp.callback_query()
    async def handle_callback_query(callback_query: types.CallbackQuery) -> None:
        """Handle inline keyboard button presses."""
        data = callback_query.data
        
        # Map button callbacks to actions
        button_actions = {
            "btn_labs": "/labs",
            "btn_scores": "/scores",
            "btn_lowest": "Which lab has the lowest pass rate?",
            "btn_top": "Who are the top 5 students?",
            "btn_sync": "Sync the data from autochecker",
            "btn_help": "/help",
        }
        
        action = button_actions.get(data, "")
        if action:
            await callback_query.answer()
            
            if action.startswith("/"):
                # It's a command - use command handler
                if action == "/labs":
                    response = handle_labs()
                elif action == "/help":
                    response = handle_help()
                elif action == "/scores":
                    response = "Usage: /scores <lab> (e.g., /scores lab-04). Use /labs to see available labs."
            else:
                # Natural language query
                response = handle_message(action, debug=True)
            
            await callback_query.message.answer(response)

    await dp.start_polling(bot)


def main() -> None:
    parser = argparse.ArgumentParser(description="LMS Telegram Bot")
    parser.add_argument(
        "--test",
        type=str,
        metavar="COMMAND",
        help="Run in test mode with the given command (e.g., '/start' or 'which lab has the lowest pass rate?')",
    )

    args = parser.parse_args()

    if args.test:
        run_test_mode(args.test)
    else:
        asyncio.run(run_telegram_mode())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Telegram bot entry point with --test mode.

Usage:
    uv run bot.py --test "/start"    # Test mode (no Telegram connection)
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
)
from config import load_settings

# aiogram imports
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

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
    parts = command.strip().split(maxsplit=1)
    cmd = parts[0]
    args = parts[1] if len(parts) > 1 else ""

    handler = get_handler(cmd)

    if cmd == "/scores":
        response = handler(args)
    else:
        response = handler()

    print(response)
    sys.exit(0)


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
        await message.answer(response)

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
    async def handle_unknown_message(message: types.Message) -> None:
        """Handle unknown commands/messages."""
        response = handle_unknown()
        await message.answer(response)

    await dp.start_polling(bot)


def main() -> None:
    parser = argparse.ArgumentParser(description="LMS Telegram Bot")
    parser.add_argument(
        "--test",
        type=str,
        metavar="COMMAND",
        help="Run in test mode with the given command (e.g., '/start')",
    )

    args = parser.parse_args()

    if args.test:
        run_test_mode(args.test)
    else:
        asyncio.run(run_telegram_mode())


if __name__ == "__main__":
    main()

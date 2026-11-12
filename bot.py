"""Backward-compatible launcher for the HS1 VPN Telegram bot."""

import asyncio
import logging

from main import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger("hs1_telegram_bot").info("Bot stopped")

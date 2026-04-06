import os
import sys
import logging
import asyncio
from pyrogram import Client
import bot.handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def run_bot():
    api_id = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    session_string = os.environ.get("SESSION_STRING")

    if not api_id or not api_hash:
        logger.error("API_ID and API_HASH environment variables are required.")
        sys.exit(1)

    if session_string:
        logger.info("Starting Pyrogram with SESSION_STRING (Userbot Mode)")
        app = Client(
            "my_userbot",
            api_id=int(api_id),
            api_hash=api_hash,
            session_string=session_string
        )
    elif bot_token:
        logger.info("Starting Pyrogram with TELEGRAM_BOT_TOKEN (Bot Mode)")
        app = Client(
            "my_bot",
            api_id=int(api_id),
            api_hash=api_hash,
            bot_token=bot_token
        )
    else:
        logger.error("Either TELEGRAM_BOT_TOKEN or SESSION_STRING is required.")
        sys.exit(1)

    logger.info("Bot is starting up. Note: Background workers run in a separate process.")
    bot.handlers.register_handlers(app)

    await app.start()

    # Keep the bot running
    try:
        from pyrogram import idle
        await idle()
    finally:
        await app.stop()

def main():
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()

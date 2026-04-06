import os
from dotenv import load_dotenv
load_dotenv("config.env")

import os
import sys
import logging
import asyncio
from pyrogram import Client
import bot.handlers
from core.redis import redis_client
from redis.exceptions import ConnectionError

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

    # Health check: Ensure Redis is accessible before starting the bot
    try:
        logger.info("Checking Redis connection...")
        await redis_client.ping()
        logger.info("Redis connection successful!")
    except Exception as e:
        logger.fatal(
            "CRITICAL: Could not connect to Redis!\n"
            "The bot requires a running Redis server to function.\n"
            f"Current REDIS_URL: {os.environ.get('REDIS_URL', 'redis://localhost:6379/0')}\n"
            "Please ensure Redis is running or check your REDIS_URL config.\n"
            f"Detailed error: {e}"
        )
        sys.exit(1) # Gracefully exit here!

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
    try:
        asyncio.run(run_bot())
    except SystemExit:
        # Expected exit on sys.exit(1)
        pass
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()

import os
import sys
import logging
from pyrogram import Client
import bot.handlers  # This will register the handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
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

    logger.info("Bot is starting up...")

    # Store app reference in handlers module so we can use decorators
    bot.handlers.register_handlers(app)

    app.run()

if __name__ == "__main__":
    main()

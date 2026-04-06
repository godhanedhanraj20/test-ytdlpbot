# Telegram Video Downloader Bot (Pyrogram)

A production-ready Telegram bot that downloads videos using `yt-dlp` and sends them back to the user.
Powered by Pyrogram, supporting regular bot accounts (50MB limit) or Premium Userbots (4GB limit).

## Requirements

- Python 3.11.9
- Telegram API Credentials (`API_ID`, `API_HASH`) from my.telegram.org
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather) OR a Pyrogram Session String (for Userbot/Premium 4GB capabilities)

## Setup

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your environment variables:
   ```bash
   export API_ID="your-api-id"
   export API_HASH="your-api-hash"
   export TELEGRAM_BOT_TOKEN="your-bot-token" # If using a regular bot
   export SESSION_STRING="your-pyrogram-session-string" # If using a userbot for 4GB uploads
   ```

## Running Locally

Run the bot using:
```bash
python -m bot.main
```

## Deployment (Heroku)

This project includes a `Procfile` and `runtime.txt` ready for Heroku deployment.

1. Create a new Heroku app.
2. Set the `API_ID`, `API_HASH`, and `TELEGRAM_BOT_TOKEN` or `SESSION_STRING` config vars in the Heroku dashboard.
3. Push the code to Heroku.
4. Scale the worker dyno:
   ```bash
   heroku ps:scale worker=1
   ```

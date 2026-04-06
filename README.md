# Telegram Video Downloader Bot

A production-ready Telegram bot that downloads videos using `yt-dlp` and sends them back to the user.

## Requirements

- Python 3.11.9
- A Telegram Bot Token from @BotFather

## Setup

1. Clone the repository.
2. Install dependencies:
   pip install -r requirements.txt
3. Set your Telegram Bot Token as an environment variable:
   export TELEGRAM_BOT_TOKEN="your-bot-token"

## Running Locally

Run the bot using:
python -m bot.main

## Deployment (Heroku)

This project includes a `Procfile` and `runtime.txt` ready for Heroku deployment.

1. Create a new Heroku app.
2. Set the `TELEGRAM_BOT_TOKEN` config var in the Heroku dashboard.
3. Push the code to Heroku.
4. Scale the worker dyno:
   heroku ps:scale worker=1

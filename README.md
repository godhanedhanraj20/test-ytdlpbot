# Telegram Video Downloader Bot (Pyrogram + Redis + ARQ)

A production-ready Telegram bot that downloads videos using `yt-dlp` and sends them back to the user.
Powered by Pyrogram, supporting regular bot accounts (50MB via Bot API, 2GB via local API) or Premium Userbots (4GB limit).

## Features & Architecture

Built with stability, scalability, and UX in mind:
- **Separation of Concerns:** The architecture splits responsibilities cleanly: the Bot handles Telegram UI/Uploading, while the Background Worker handles CPU-heavy `yt-dlp` downloading.
- **ARQ Redis Queue:** Eliminates CPU/RAM exhaustion by delegating concurrent downloads to resilient, asynchronous background workers.
- **Redis Progress Tracking:** The worker writes live download metrics to Redis, and the bot polls them. This prevents multiple open Telegram connections and avoids Premium session invalidation.
- **Smart Format UI:** Categorizes available download options with clear emojis (🎥 Video, 🎵 Audio), resolutions, formats, and estimated file sizes for easy selection.
- **Live Progress Bars:** Displays visual ASCII progress bars (`[██████....] 65%`) and calculated transfer speeds.
- **Graceful Cancellation:** Supports a `/cancel` command to safely abort active Redis jobs.
- **Anti-Spam Locks:** Enforces a per-user lock stored in Redis ensuring users cannot spam requests and crash the bot.

## Requirements

- Python 3.11.9
- Redis Server (local, remote, or via Docker)
- Telegram API Credentials (`API_ID`, `API_HASH`) from my.telegram.org
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather) OR a Pyrogram Session String (for Userbot/Premium 4GB capabilities)

## Setup & Deployment

You can deploy the bot using Docker (Recommended for VPS) or natively (Heroku).

### 1. Configure Environment Variables

First, rename the provided template:
```bash
cp sample.config.env config.env
```
Then open `config.env` and fill in your details (API ID, Hash, Token, etc.).

### 2. VPS Deployment (Docker Compose - Recommended)

Once `config.env` is configured, run using Docker Compose:
```bash
docker-compose up -d --build
```
This will spin up the `redis`, `bot`, and `worker` containers, passing your environment variables and sharing the `/downloads` folder automatically.

### 3. Native / Heroku Deployment

If you prefer native execution:
1. Ensure Redis is running locally or remotely.
2. Load your environment variables from your terminal:
   ```bash
   export $(grep -v '^#' config.env | xargs)
   ```
3. Run the Bot and Worker in separate terminals:
   ```bash
   python -m bot.main
   arq core.worker.WorkerSettings
   ```

For **Heroku**, a `Procfile` is provided. Simply provision a Heroku Redis add-on, manually copy the config values from your `config.env` into the Heroku Dashboard Config Vars, and scale both dynos:
```bash
heroku ps:scale bot=1 worker=1
```

## How to Use & Workflow

1. **Start:** Send `/start` to the bot.
2. **Send URL:** Send a supported video URL (YouTube, Twitter, TikTok, etc.).
3. **Select Format:** Tap an option from the inline keyboard. The bot pushes a job to Redis.
4. **Processing:** The ARQ worker downloads the video, sending progress data back to Redis. The bot polls this data and updates your Telegram UI.
5. **Upload:** Once the worker completes the file, the Bot reads the result and uploads it to you natively.

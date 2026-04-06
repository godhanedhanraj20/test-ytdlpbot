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

### 1. VPS Deployment (Docker Compose - Recommended)

Create a `.env` file in the project root:
```bash
API_ID=your_api_id
API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token
# SESSION_STRING=your_session_string
```

Run using Docker Compose:
```bash
docker-compose up -d --build
```
This will spin up the `redis`, `bot`, and `worker` containers, sharing the `/downloads` folder automatically.

### 2. Native / Heroku Deployment

If you prefer native execution:
1. Ensure Redis is running and set `REDIS_URL` in your environment (default: `redis://localhost:6379/0`).
2. Set API keys:
   ```bash
   export API_ID="your-api-id"
   export API_HASH="your-api-hash"
   export TELEGRAM_BOT_TOKEN="your-bot-token"
   ```
3. Run the Bot and Worker in separate terminals:
   ```bash
   python -m bot.main
   arq core.worker.WorkerSettings
   ```

For **Heroku**, a `Procfile` is provided. Simply provision a Heroku Redis add-on, set config vars, and scale both dynos:
```bash
heroku ps:scale bot=1 worker=1
```

## How to Use & Workflow

1. **Start:** Send `/start` to the bot.
2. **Send URL:** Send a supported video URL (YouTube, Twitter, TikTok, etc.).
3. **Select Format:** Tap an option from the inline keyboard. The bot pushes a job to Redis.
4. **Processing:** The ARQ worker downloads the video, sending progress data back to Redis. The bot polls this data and updates your Telegram UI.
5. **Upload:** Once the worker completes the file, the Bot reads the result and uploads it to you natively.

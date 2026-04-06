# Telegram Video Downloader Bot (Pyrogram)

A production-ready Telegram bot that downloads videos using `yt-dlp` and sends them back to the user.
Powered by Pyrogram, supporting regular bot accounts (50MB limit via Bot API or 2GB via Pyrogram local API) or Premium Userbots (4GB limit).

## Features & Architecture

Built with stability and scalability in mind:
- **Download Queue:** Prevents CPU/RAM exhaustion by limiting concurrent downloads using background asyncio workers.
- **Anti-Spam Locks:** Enforces a per-user lock ensuring users cannot spam requests and crash the bot.
- **Disk Space Protection:** Automatically verifies server storage before starting large downloads to prevent disk full errors.
- **Robust Caching:** Uses a TTL-based URL and metadata cache, avoiding Telegram's 64-byte payload limit and preventing memory leaks.
- **Live Progress Updates:** Hooked directly into `yt-dlp` to provide real-time feedback on download percentage and speed.
- **Format Filtering:** intelligently groups and sorts available formats, keeping the UI clean and responsive.

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

## How to Use & Workflow

Once the bot is running, interacting with it is simple. Here is the step-by-step workflow:

### 1. Initialization Command
- **Command:** `/start`
- **Action:** Send this command to the bot to verify it is running. The bot will reply with a welcome message and basic usage instructions.

### 2. Provide a Video URL
- **Action:** Send the bot a valid HTTP/HTTPS link to a video from any platform supported by `yt-dlp` (e.g., YouTube, TikTok, Twitter/X, Instagram, Vimeo).
- **Example:** `https://www.youtube.com/watch?v=dQw4w9WgXcQ`

### 3. Format Selection
- **Action:** Once you send the link, the bot will parse the URL and extract the available formats without downloading the video.
- **Result:** You will receive an **Inline Keyboard Menu** containing the available qualities (e.g., 1080p, 720p, Audio only), file formats (.mp4, .webm), and estimated file sizes.
- **Next Step:** Tap on the button corresponding to your desired format.

### 4. Downloading and Uploading
- **Action:** After clicking your desired format, the bot will begin downloading the video to its local storage. It will update the message periodically to reflect its progress (`Downloading... Progress: 45% Speed: 2MiB/s`).
- **Result:** Once the download is complete, the bot automatically uploads the file directly to your Telegram chat. After a successful upload, the bot deletes the local file to save space.

### Note on File Size Limits
- **Regular Bot (Bot Token):** Can upload files up to 2GB using Pyrogram.
- **Premium Userbot (Session String):** If logged in via a `SESSION_STRING` attached to a Telegram Premium account, the upload limit is increased to 4GB.

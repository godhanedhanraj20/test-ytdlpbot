# 🎥 Telegram Video Downloader Bot

A powerful, production-ready Telegram bot that downloads videos using `yt-dlp` and sends them back to you directly inside Telegram!

Powered by **Pyrogram** and **Redis**, this bot supports massive file uploads (up to 4GB with Telegram Premium) and can handle multiple users at once without crashing thanks to its background queue system.

---

## ✨ Features

- 🔒 **Private Mode & Admin Panel:** Secure the bot for your own use. Access an interactive Control Panel (`/ytdlp_bs`) to view live User Analytics, Active Jobs, Queue Size, and to seamlessly Pause/Resume operations globally.
- ⚙️ **Personalized User Settings:** Every user can customize their experience (`/ytdlp_us`) by setting a default Download Quality, Media Type (Video/Document), Custom Prefix/Suffix for filenames, and a Custom Thumbnail!
- 📝 **On-The-Fly Renaming:** Tap a video format, and the bot will instantly prompt you to enter a custom filename right in the chat (or skip it) before pushing the download to the worker queue.
- ⭐ **Auto-Best Mode:** Users can toggle Auto-Best to entirely skip the format selection screen, making downloads instantly pipe to the background worker.
- 🚀 **Queue System (ARQ):** Downloads happen in the background. The bot never freezes!
- 📊 **Beautiful Live UI:** Custom "Obsidian Media Node" branding dynamically renders detailed download/upload speeds, queue positions, precise ETA, and live Bot Server Stats (CPU/RAM).
- 🛡️ **Anti-Bot Bypass:** Uses advanced `yt-dlp` settings to bypass YouTube's "Sign in to confirm you're not a bot" checks without requiring cookies.
- 🔄 **Intelligent Fallbacks:** Automatically retries downloads using safe fallback formats if the preferred quality fails or encounters HTTP 403 errors.
- 🎨 **Smart UI:** Video formats are sorted cleanly (e.g., `🎥 1080p`) with clear `🔊` (Audio) and `🔇` (Mute) indicators.
- 🖼 **Video Previews:** Get thumbnail previews and duration before selecting the video format to download.
- 🛑 **Cancel Anytime:** Made a mistake? Just click the inline ❌ Cancel button to stop your active download instantly and exclusively (without affecting other users in the queue).
- 🚦 **Anti-Spam & Limits:** Built-in rate limiting and disk-space checks keep your server safe.

---

## 🛠️ Prerequisites

Before starting, you will need:
1. **Python 3.11+** and **FFmpeg** installed on your computer/server (FFmpeg is required to safely merge high-quality video/audio streams).
2. A **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather)).
3. **API ID & API HASH** (from [my.telegram.org](https://my.telegram.org)).
4. A **Redis** database (local, Docker, or a free cloud provider like Redis Cloud).

*(Optional)* A Pyrogram **Session String** if you want to use a Premium Telegram account to upload files up to 4GB.

---

## ⚙️ Initial Setup (Do this first!)

Clone the repository and install the requirements:

```bash
git clone https://github.com/your-username/video-bot.git
cd video-bot
pip install -r requirements.txt
```

Next, set up your configuration file:

```bash
cp sample.config.env config.env
```

**Important Details to configure in `config.env`:**
1. Fill in `API_ID` and `API_HASH`
2. Fill in `TELEGRAM_BOT_TOKEN`
3. Fill in `REDIS_URL`
4. Set `ADMIN_USER_ID` (your own Telegram user ID) to secure your bot and enable access to the admin commands.

---

## 🚀 Deployment Options

Choose the deployment method that fits your needs.

| Deployment Type | Difficulty | Cost | Best For |
| :--- | :--- | :--- | :--- |
| **💻 Local** | ⭐ Easy | Free | Developers testing code on their own computer. |
| **🧪 Testing (Google Cloud)** | ⭐⭐ Medium | Free | Complete beginners wanting to test a bot online for free without adding a credit card. |
| **☁️ Heroku** | ⭐⭐ Medium | Paid/Free | Quick scaling and native integration. |
| **🐳 VPS (Docker)** | ⭐⭐⭐ Hard | ~$5/mo | **Production!** 24/7 uptime, massive storage, and perfect stability. |

---

### 💻 Local Deployment

Run the bot directly on your PC or inside Google Cloud Shell for development.

1. Ensure Redis is running (or you have a free `REDIS_URL` in `config.env`).
2. Run the helper script to start **both the bot and the worker process concurrently** in one terminal:
   ```bash
   python3 run.py
   ```
3. To stop the bot and the worker gracefully, press `Ctrl+C`.

---

### 🧪 Testing Deployment (Google Cloud Free Tier)

**Perfect for complete beginners with a fresh Gmail account! No billing required.**

We have written a comprehensive, step-by-step guide specifically for deploying this bot on Google Cloud Run for free. It explains how to get a free Redis database and how to navigate the Google console.

👉 **[Read the Full Testing Guide Here](Testing/Testing.md)**

---

### ☁️ Heroku Deployment

Deploy natively to Heroku using the provided `Procfile`.

1. Create a new Heroku App.
2. Provision a **Heroku Redis** add-on.
3. In the Heroku Dashboard, copy your `config.env` variables into the **Config Vars** section.
4. Push your code to Heroku.
5. Important: Scale *both* processes (Bot and Worker):
   ```bash
   heroku ps:scale bot=1 worker=1
   ```

---

### 🐳 VPS Deployment (Docker Compose - Recommended)

For serious 24/7 usage, renting a cheap $5/mo VPS (like DigitalOcean, Hetzner, or Linode) is highly recommended.

1. Install Docker on your VPS.
2. Fill out your `config.env`.
3. Run the following command:
   ```bash
   docker-compose up -d --build
   ```
This automatically spins up Redis, the Bot, and the Worker in isolated containers and shares the `/downloads` folder seamlessly.

---

---

## 🛡️ Bypassing YouTube Anti-Bot & 403 Errors

YouTube has recently introduced aggressive anti-bot mechanisms that block downloads originating from datacenter IP addresses (like Google Cloud, AWS, or DigitalOcean) with errors like:
* `HTTP Error 403: Forbidden`
* `Sign in to confirm you’re not a bot`
* `Video requires login or is age-restricted`

**How this bot overcomes it:**
This bot is designed to be highly resilient to these blocks *without* requiring cookies.
1. **Dynamic JS Solvers:** The bot utilizes `yt-dlp`'s default web clients which can solve obfuscated JavaScript challenges dynamically (Requires Node.js installed on your server).
2. **Intelligent Format Fallbacks:** If a preferred high-quality format is blocked, the worker automatically retries downloading the next `best` available stream before giving up.
3. **Smart Error Handling:** If an IP is permanently banned or a video is strictly age-restricted, the bot intercepts the crash and sends a user-friendly message rather than a raw stack trace.

**How YOU can fix persistent 403 errors:**
If you continue to get these errors on every video, your server's IP address has been flagged by YouTube.
* **Fix A:** Run the bot on a **residential internet connection** (like your local PC at home).
* **Fix B:** Deploy the bot on a VPS and configure your server to route `yt-dlp` traffic through an IPv6 proxy or a residential VPN.
* **Fix C (Advanced):** Manually provide an `oauth2` token or `--cookies` file inside the `services/downloader.py` configuration.

---

## 🎮 How to Use

1. Open Telegram and send `/start` to your bot.
2. Send any valid video link (YouTube, TikTok, Twitter, etc.).
3. The bot will reply with an inline keyboard full of options.
4. Click the format you want. The bot will handle the rest in the background!

**Admin Commands:**
- `/adduser <telegram_id>`: Allow a friend to use the bot.
- `/ytdlp_bs`: Open the interactive Admin Control Panel to view analytics (Total Users, Active Jobs, Queue Size) and globally Pause/Resume the bot.

**User Commands:**
- `/ytdlp_us`: Open your Personalized Settings (Quality, Mode, Filename Prefix/Suffix, Thumbnail).
- `/cancel`: Stop your active download/upload safely.
- `/reset`: Force-unlock your account if the bot accidentally crashes while you were downloading.

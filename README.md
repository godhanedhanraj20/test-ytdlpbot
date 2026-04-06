# 🎥 Telegram Video Downloader Bot

A powerful, production-ready Telegram bot that downloads videos using `yt-dlp` and sends them back to you directly inside Telegram!

Powered by **Pyrogram** and **Redis**, this bot supports massive file uploads (up to 4GB with Telegram Premium) and can handle multiple users at once without crashing thanks to its background queue system.

---

## ✨ Features

- 🔒 **Private Mode:** Lock the bot down so only you (and people you `/adduser`) can use it.
- 🚀 **Queue System (ARQ):** Downloads happen in the background. The bot never freezes!
- 📊 **Live Progress Bars:** Watch the download and upload speeds in real-time.
- 🎨 **Smart UI:** Video formats are sorted cleanly (e.g., `🎥 1080p`) with clear `🔊` (Audio) and `🔇` (Mute) indicators.
- 🛑 **Cancel Anytime:** Made a mistake? Just type `/cancel` to stop your active download.
- 🚦 **Anti-Spam & Limits:** Built-in rate limiting and disk-space checks keep your server safe.

---

## 🛠️ Prerequisites

Before starting, you will need:
1. **Python 3.11+** installed on your computer/server.
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
Open `config.env` in a text editor and fill in your API details, Bot Token, and Redis URL. If you want the bot to be private, put your Telegram User ID in `ADMIN_USER_ID`.

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
2. Run the helper script to start **both the bot and the worker** in one terminal:
   ```bash
   python3 run.py
   ```
3. To stop the bot, press `Ctrl+C`.

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

## 🎮 How to Use

1. Open Telegram and send `/start` to your bot.
2. Send any valid video link (YouTube, TikTok, Twitter, etc.).
3. The bot will reply with an inline keyboard full of options.
4. Click the format you want. The bot will handle the rest in the background!

**Admin Commands:**
- `/adduser <telegram_id>`: Allow a friend to use the bot.

**User Commands:**
- `/cancel`: Stop your active download/upload safely.
- `/reset`: Force-unlock your account if the bot accidentally crashes while you were downloading.

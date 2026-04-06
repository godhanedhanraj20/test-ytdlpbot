# How to Test and Deploy Your Telegram Bot on Google Cloud (Free)

Welcome! This guide is written for complete beginners. You do not need to be a developer to follow this. We will walk you step-by-step through setting up, testing, and running your new Telegram Video Downloader bot using Google Cloud's free tools.

**Please read everything carefully.**

---

## 1. 🧾 Prerequisites (What you need before starting)

Before touching any code, you need three things:

1. **A Google Account:** A fresh, normal Gmail account is perfect.
2. **A Telegram Bot Token:**
   - Open Telegram and search for `@BotFather`.
   - Send him the message `/newbot` and follow his instructions to pick a name.
   - He will give you a long string of text called a **Token** (it looks like `123456789:ABCdefGhIjkLmnop...`). Save this!
3. **Telegram API Credentials (`API_ID` and `API_HASH`):**
   - Go to [my.telegram.org](https://my.telegram.org) in your web browser.
   - Log in with your phone number.
   - Click on "API development tools".
   - Fill in a random app title and short name, then click create.
   - You will see your **App api_id** (a number) and **App api_hash** (a long mix of letters and numbers). Save both!

---

## 2. ⚠️ The Redis Problem (Important First Step)

Our bot is very powerful because it uses a system called **Redis**. Redis acts like a waiting room for downloads so the bot doesn't crash when many people use it.

**The Problem:** Google Cloud does not give you a free Redis waiting room.

**The Solution (Use Redis Cloud):**
We will get a free waiting room from another website first!

1. Go to [Redis Cloud](https://redis.com/try-free/) and sign up for a free account.
2. Create a "Free Subscription" database.
3. Once created, look for the **Public Endpoint** (it looks like `redis-12345.c1.us-east-1-2.ec2.cloud.redislabs.com:12345`).
4. Look for the **Default User Password** under security settings.
5. Your `REDIS_URL` will look like this:
   `redis://default:YOUR_PASSWORD_HERE@YOUR_PUBLIC_ENDPOINT_HERE`
   *(Example: `redis://default:AbCdEf1234@redis-12345.c1.us-east-1-2.ec2.cloud.redislabs.com:12345`)*
   **Save this `REDIS_URL` safely.**

---

## 3. ☁️ Google Cloud Setup

Let's prepare your free Google Cloud account.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Accept the terms of service.
3. **Create a Project:** Click the dropdown at the very top left (next to the Google Cloud logo) and click "New Project". Name it something like `my-telegram-bot`.
4. **Enable Services:** In the top search bar, search for **Cloud Run API** and click "Enable". Do the same for **Artifact Registry API**.

*(Honest Warning: Google Cloud gives you a massive free tier that resets every month. As long as you stay within the free limits, you won't be charged. However, they may ask you to link a credit card just to verify you are a real person. They will not charge it unless you manually upgrade.)*

---

## 4. 🐳 Preparing the Code (Docker)

To put our bot on Google Cloud, we have to pack it into a box. Developers call this box "Docker".

1. **Install Docker:** Go to [docker.com](https://www.docker.com/products/docker-desktop/) and download Docker Desktop for your computer (Windows or Mac). Install it and open it.
2. **Open Terminal/Command Prompt:** Open the terminal on your computer and navigate to the folder where your bot code is.
3. **Build the Box:** Type this exact command and press Enter:
   ```bash
   docker build -t telegram-bot .
   ```
   *This takes all the code and puts it inside a neat package ready for the cloud.*

---

## 5. 🚀 Deploying the Bot to Cloud Run

Now we send the box to Google.

1. Go back to Google Cloud Console, search for **Cloud Run**, and click it.
2. Click **Create Service**.
3. Choose "Deploy one revision from an existing container image". *(Note: You will need to push your local docker image to Google Artifact Registry first, or you can link your GitHub account directly to Cloud Run for easiest deployment!)*
4. **Environment Variables:** This is the most important part! Scroll down to the "Container, Variables & Secrets" section, click "Variables", and add these:
   - Name: `API_ID` | Value: *(Your API ID from step 1)*
   - Name: `API_HASH` | Value: *(Your API HASH from step 1)*
   - Name: `TELEGRAM_BOT_TOKEN` | Value: *(Your Bot Token from step 1)*
   - Name: `REDIS_URL` | Value: *(Your Redis URL from step 2)*
5. Click **Deploy**.

---

## 6. 🔄 The Background Worker Setup

Our bot has two halves:
- The **Bot** (talks to users on Telegram)
- The **Worker** (does the heavy lifting of downloading videos)

Google Cloud Run is "stateless", meaning it goes to sleep when no one is talking to it. This is bad for long video downloads!

**How to fix this:**
You must deploy a *second* Cloud Run service just for the worker.
1. Repeat the exact same steps in **Section 5** to create another Cloud Run service.
2. Add all the exact same Environment Variables.
3. Change the "Container Command" (in the container settings) to:
   `arq core.worker.WorkerSettings`
4. Deploy it! Now your bot can talk to users, and your worker handles downloads.

---

## 7. 🧪 Testing the Bot

Time to see if it works!

1. Open Telegram and search for the bot name you created with `@BotFather`.
2. Click **Start** (or type `/start`). The bot should reply with a welcome message!
3. **Send a video link** (like a YouTube or TikTok link).
4. The bot will show you buttons for Video and Audio formats.
5. Click a format.
6. You should see a live progress bar as it downloads, and then it will send the video directly to you!

---

## 8. 🧨 Common Errors (And How to Fix Them)

If things break, don't panic! Check these common issues:

- **Bot is not responding at all:**
  - *Fix:* You likely typed your `TELEGRAM_BOT_TOKEN` wrong. Double-check it in Google Cloud Run variables.
- **Bot responds, but nothing downloads (stuck on queued):**
  - *Fix:* Your Worker is not running, or your `REDIS_URL` is wrong. Ensure your free Redis Cloud database is active and both the Bot and Worker have the exact same `REDIS_URL`.
- **Bot sends an error "Could not extract video info":**
  - *Fix:* The link you sent might be private, broken, or not supported by `yt-dlp`. Try a normal, public YouTube video to test.
- **"Server disk space is low":**
  - *Fix:* Google Cloud Run gives very little storage space. If you download massive files, it fills up. (See Section 9).

---

## 9. 💡 Honest Advice: Is Google Cloud the best choice?

**Short answer:** No.

Google Cloud Run is amazing for testing, but it has strict limitations:
1. **Timeouts:** Cloud Run kills processes after a few minutes. Huge video downloads might get cancelled automatically.
2. **Storage:** You get very little temporary disk space.
3. **Sleeping:** Cloud Run goes to sleep to save money, making the bot feel slow to wake up.

**Recommended Path for the Future:**
Once you are happy testing the bot here, we highly recommend renting a cheap **VPS** (Virtual Private Server) from companies like **DigitalOcean, Hetzner, or Linode** (costs ~$5 a month).

On a VPS, the bot never sleeps, it has a massive hard drive for huge 4GB files, and you can run the Bot, the Worker, and Redis all on the exact same machine using the `docker-compose.yml` file included in this code. It is vastly superior and much easier to manage long-term!

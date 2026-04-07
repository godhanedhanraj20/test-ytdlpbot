# Obsidian Media Node - Complete Functionality Guide

This document outlines every feature, command, button, and user flow currently available in the Obsidian Media Node (Telegram Video Downloader Bot).

---

## 1. 🚀 Standard User Commands

These commands are available to any user who has been whitelisted to use the bot.

| Command | Description | Example Usage |
| :--- | :--- | :--- |
| `/start` | Initializes the bot, tracks the user in the database, and displays the welcome message. | `/start` |
| `/cancel` | Instantly aborts the user's active download or upload. | `/cancel` |
| `/reset` | Forcefully deletes the user's active database lock if a download gets permanently stuck. | `/reset` |
| `/ytdlp_us` | Opens the **Personalized User Settings** menu. | `/ytdlp_us` |

### 💬 `/start` Message Example
```text
⚡ Obsidian Media Node

High-performance media downloader.
Send a link to begin.

💡 /cancel - stop active download
🔄 /reset - unstick your account
```

---

## 2. 👑 Admin Commands

These commands are strictly restricted to the user whose Telegram ID matches `ADMIN_USER_ID` in `config.env`.

| Command | Description | Example Usage |
| :--- | :--- | :--- |
| `/adduser` | Whitelists a specific Telegram User ID so they can interact with the bot. | `/adduser 123456789` |
| `/ytdlp_bs` | Opens the **Admin Control Panel** to monitor live statistics and manage bot state. | `/ytdlp_bs` |

---

## 3. 📥 The Downloading Flow

When a user sends a valid HTTP/HTTPS media link (YouTube, TikTok, Twitter, etc.), the bot follows this precise flow:

### Phase A: Video Preview
Before downloading, the bot securely fetches the metadata (bypassing anti-bot checks) and presents a rich preview:
```text
🎬 **SPIDER-MAN - Official Trailer**
⏱ Duration: 2m 15s

Select a format to download:
```
*Inline Buttons:*
* `[🎥 1080p (video only, will merge audio) MP4 – 15.0MB ⭐]` *(Best recommended format)*
* `[🎥 720p (with audio) MP4 – 8.5MB]`
* `[Audio 🎵 M4A – 2.0MB]`
* `[❌ Cancel]`

### Phase B: On-The-Fly Renaming
After clicking a format (unless `Auto Best` is ON), the bot suspends the download and prompts the user to either customize the final file name, or skip:
```text
✏️ **Enter a new filename** for this download.

Or tap **Skip** to keep the original name.
*(Timeout: 5 minutes)*
```
*Inline Buttons:*
* `[⏭ Skip]`
* `[❌ Cancel]`

*If the user types "My Vacation Video" in the chat, the bot sanitizes the input and renames the file automatically before uploading it to Telegram.*

### Phase C: Live Progress UI
Once a format is selected, the bot initiates the ARQ worker queue and begins the download. The UI updates dynamically:
```text
**SPIDER-MAN - Official Trailer**
┃ 〖✦✦✦✦✦✧✧✧✧✧〗 54.28%
┠ Processed: 1.94GB of 3.58GB
┠ Status: 📥 Download | ETA: 3m
┠ Speed: 9.29MB/s | Elapsed: 6m56s
┠ Engine: Obsidian Media Node | Pyrogram
┠ User: Randy | ID: 6502443202
┖ /cancel

⌬ Bot Stats
┠ CPU: 34.2% | F: 227.88GB [64.9%]
┖ RAM: 46.5% | UPTIME: 2h46m35s
```
*Inline Buttons:*
* `[❌ Cancel]`

### Phase D: Completion
Upon successful upload to Telegram, the bot sends the video alongside a summary:
```text
✅ **Obsidian Node Complete**
🎬 SPIDER-MAN - Official Trailer

⏱ Total time: 10m 15s
📦 Size: 3.58GB
```

---

## 4. ⚙️ Personalized User Settings (`/ytdlp_us`)

Each user can open `/ytdlp_us` to customize how the bot handles their media. These settings are persistently stored in Redis.

### 🖼️ UI Panel
```text
⚙️ **User Settings**

🎬 **Mode:** 🎬 Video
📄 **Send As:** 📺 Media
🎥 **Quality:** 🤔 Ask Every Time
🖼 **Thumbnail:** ❌ Not Set
✏️ **Prefix:** None
✏️ **Suffix:** None
```

### 🔘 Interactive Buttons & Usage

| Button Name | Behavior / Usage |
| :--- | :--- |
| `Mode: 🎬 Video` / `🎵 Audio` | Toggles the default extraction mode. If set to Audio, sending a link will only extract `.mp3`/`.m4a`. |
| `Send As: 📺 Media` / `📄 Doc` | Toggles whether Telegram renders the file as a playable Video/Audio track, or strictly as an uncompressed File/Document. |
| `🎥 Quality Preference` | Opens a submenu allowing the user to force a specific resolution (e.g., `1080p`, `720p`, or `Best`). |
| `⭐ Auto Best: ON/OFF` | **Crucial Feature.** If ON, the bot skips the "Phase A: Video Preview" screen entirely and immediately downloads the highest quality stream. |
| `🖼 Custom Thumbnail` | Prompts the user to send an image. The bot saves this image and applies it as the cover art for all their future downloads. |
| `🗑 Clear Thumb` | Erases the custom thumbnail. |
| `✏️ Set Prefix / Suffix` | Prompts the user for a text tag. Example: Setting prefix to `[Obsidian]` will rename `SpiderMan.mp4` to `[Obsidian] SpiderMan.mp4` automatically before upload. |
| `🗑 Clear Tags` | Erases any saved Prefix or Suffix. |

---

## 5. 🎛️ Admin Control Panel (`/ytdlp_bs`)

The bot owner can monitor the node's health via `/ytdlp_bs`.

### 🖼️ UI Panel
```text
⚙️ **Obsidian Media Node Control Panel**

🚦 Status: ▶️ ACTIVE
👥 Total Users: 12
📥 Active Jobs: 2
📦 Queue Size: 3
```

### 🔘 Interactive Buttons & Usage

| Button Name | Behavior / Usage |
| :--- | :--- |
| `📊 Stats` | Refreshes the panel to pull the latest concurrent user, queue, and active job metrics from Redis. |
| `🧹 Clear Queue` | (Placeholder) Intended to wipe pending ARQ jobs from memory if the node gets flooded. |
| `⛔ Pause Bot` | Sets a global Redis flag (`bot:paused`). Any non-admin user who sends a link will be rejected with: `⛔ The node is currently paused for maintenance.` |
| `▶️ Resume Bot` | Unpauses the bot, allowing normal downloads to resume. |
| `⚙️ Settings` | Reserved for future advanced dynamic limits (e.g., tweaking rate limits or max file sizes on the fly). |

---

## 6. 🛡️ Architectural & Background Features

These features operate invisibly to protect the user and the server:
- **On-The-Fly Renaming:** Intercepts format selections dynamically, allowing users to rename files natively in the chat using a secure `sanitize_filename` helper before touching the filesystem.
- **Intelligent Audio Merging:** If a user selects a Video-Only stream (like standard 1080p), the worker automatically fetches the highest-quality audio stream and merges them using `ffmpeg` before uploading.
- **Anti-Bot Bypass:** Uses advanced `yt-dlp` heuristics (Node.js engine delegation) to bypass YouTube HTTP 403 blocks and Datacenter IP bans without requiring `oauth2` or cookies.
- **Auto-Retry & Fallbacks:** If a specific format stream fails mid-download, the worker automatically re-attempts the download using the generic `best` format before throwing an error.
- **Smart Error Handling:** If an anti-bot restriction cannot be bypassed, the user receives clean instructions on how to proceed, rather than a broken stack trace.

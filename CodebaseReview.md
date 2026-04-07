# CodebaseReview.md: Obsidian Media Node Audit

This technical audit analyzes the current state of the Telegram Video Downloader bot, its architecture, performance bottlenecks, code smells, and necessary improvements. **No code has been modified; this is strictly an analysis.**

---

## 1. 🧱 Architecture Overview

The system operates on an asynchronous distributed queue model to separate the user-facing bot from the resource-intensive downloading tasks.

- **`bot/`**: Contains the Pyrogram application (`main.py`), routing logic/commands (`handlers.py`), UI templates (`ui.py`), and User Settings state (`user_settings.py`).
- **`services/`**: Contains the `yt-dlp` wrapper logic (`downloader.py`) that handles format extraction and binary file creation.
- **`core/`**: Houses utility scripts for Redis connections (`redis.py`), the ARQ worker definition (`worker.py`), persistent caching and metrics (`cache.py`), user locking (`limits.py`), and logging setup (`logger.py`).

**Data Flow:**
1. User sends a URL → `bot/handlers.py` executes.
2. Bot extracts formats synchronously via `yt-dlp` in a background thread and caches choices in Redis.
3. User selects a format → `handlers.py` acquires a Redis lock and enqueues an ARQ job.
4. `core/worker.py` picks up the job, downloads the video, and reports progress back to Redis.
5. `bot/handlers.py` continuously polls Redis for progress, updates the Telegram message UI, and upon completion, uploads the local file back to the user.

---

## 2. ❌ Broken / Incomplete Features

- **Custom Thumbnail Uploads (`/ytdlp_us`)**
  - **Problem**: The User Settings flow saves the Telegram `file_id` of a custom thumbnail to Redis. However, the bot simply passes this `file_id` directly to `client.send_document(thumb=thumbnail)`.
  - **Root Cause**: Pyrogram expects a local file path (or a properly fetched byte stream) for the `thumb` argument during media uploads, not an arbitrary `file_id` from another chat context.
  - **Affected Files**: `bot/handlers.py`, `bot/user_settings.py`

- **Global Cancellation Ambiguity**
  - **Problem**: While the `/cancel` command correctly isolates cancellations via `cancel:{user_id}`, the UI inline button uses the `cancel_job` callback query. The logic in `bot/handlers.py` is sound, but if a user has a queued job (not active), cancelling only sets the Redis flag without removing the job from ARQ's pending queue.
  - **Root Cause**: ARQ does not easily support aborting a job while it's in the `queued` state. The job will eventually run, immediately read the cancel flag, and abort—but this wastes queue space and creates a UX delay.
  - **Affected Files**: `bot/handlers.py`, `core/worker.py`

- **Audio File Extension Mismatch**
  - **Problem**: The user settings logic allows forcing a format to `audio` or extracting the best audio. However, `yt-dlp` may default to `.webm` or `.m4a`. The bot statically checks `.mp3`, `.m4a`, or `.wav` to decide whether to use `send_audio()`. If it’s `.webm` audio, it falls back to `send_document()`.
  - **Root Cause**: Brittle string-matching on the file extension instead of checking the mime-type or standardizing the `merge_output_format` in `yt-dlp` specifically for audio.
  - **Affected Files**: `bot/handlers.py`, `services/downloader.py`

---

## 3. ⚠️ Code Smells & Design Problems

- **Massive God Function (`bot/handlers.py`)**
  - The `button_callback` function handles authentication, rate limiting, ARQ enqueueing, synchronous file renaming, a heavy `while True` polling loop for progress, and the file upload sequence. It spans hundreds of lines.
- **Synchronous File IO in Async Context**
  - Functions like `os.rename(file_path, new_path)` and `os.path.getsize(final_file_path)` are executed directly inside the async Telegram handler, temporarily blocking the Pyrogram event loop.
- **Tight Coupling Between Bot and Worker**
  - The bot handles the `upload` phase, meaning the bot server must share a filesystem (e.g., `/downloads`) with the worker server. This defeats the purpose of distributed workers since they must run on the exact same node/container to share the file path.
- **Hardcoded Timeout Magic Numbers**
  - Values like `timeout=600` (10 minutes) for downloads and uploads are hardcoded globally, making it difficult to adjust for larger files or slower network connections dynamically.

---

## 4. 🔄 State Management Issues

- **Inconsistent Redis Namespacing**
  - Keys are created sporadically: `format:{short_id}`, `progress:{job_id}`, `lock:{user_id}`, `cancel:{user_id}`, `user_settings:{user_id}`, `bot:users`, `bot:active_jobs`. This lacks a cohesive pattern (e.g., prefixing everything with `om_node:`).
- **Polling vs Pub/Sub**
  - `bot/handlers.py` uses a `while True: await asyncio.sleep(3)` loop to poll Redis for progress updates. While functional, it scales poorly. If 100 users are downloading, 100 concurrent tasks are polling Redis every 3 seconds. Redis Pub/Sub would be significantly more efficient.

---

## 5. 🚨 Concurrency & Queue Risks

- **Polling Loop Race Conditions**
  - If the worker finishes the download and deletes the progress key *between* the 3-second sleep intervals in the bot, the bot might miss the final 100% progress update.
- **Thread-Safety in Progress Callbacks**
  - In `services/downloader.py`, `yt-dlp` invokes the progress hook from a background thread. While `asyncio.run_coroutine_threadsafe` is used to safely bridge to the ARQ loop, querying `is_cancel_requested(user_id)` inside the synchronous hook creates blocking network calls to Redis on every single chunk downloaded. This drastically slows down the `yt-dlp` download speed.

---

## 6. 📉 Performance Bottlenecks

- **Redis Overhead in `yt-dlp` Hook**
  - Calling `is_cancel_requested` via Redis for every single progress chunk (which can happen hundreds of times per second) is a massive bottleneck. The worker should cache the cancel flag locally or only check Redis every ~2 seconds.
- **Uploading Blocks the Bot Event Loop**
  - `client.send_document()` runs within the Pyrogram event loop. Massive 2GB uploads will hog memory and bandwidth on the bot side, rather than being offloaded to the worker.

---

## 7. 🔐 Safety & Abuse Risks

- **Lack of Global Rate Limiting**
  - While individual users are limited (e.g., 5 per 15 min), there is no global limit checking how many concurrent users are allowed. If a malicious group of 50 whitelisted users requests videos simultaneously, they could easily overwhelm the 10GB disk space or crash the Pyrogram instance.
- **No Input Sanitization for Prefix/Suffix**
  - User settings allow a 30-character prefix/suffix. This string is passed directly into `os.rename()`. A user could input `../../../etc/passwd` or similar path traversal strings, causing the bot to crash or write files to unintended locations.

---

## 8. 🎨 UX / UI Issues

- **Orphaned Callbacks**
  - If the bot restarts while a user is waiting in the `while True` loop, the bot loses track of the task. The worker will finish the download, but the user will never receive the file, leaving the UI permanently stuck on "Downloading..."
- **Format Extraction Delay**
  - Fetching YouTube formats can take up to 10 seconds. The user sees "Extracting video information..." but there is no timeout warning or interactive loading state.

---

## 9. 🧪 Missing Error Handling

- **Missing FFmpeg Fallback**
  - If `ffmpeg` is missing, `yt-dlp` is hard-aborted. The system should gracefully fall back to downloading a pre-merged format (like standard 720p MP4) instead of crashing entirely.
- **Cleanup Failures on Upload Crash**
  - If `client.send_document()` fails (e.g., due to a Telegram API error), the `finally:` block cleans up the file, but it does not gracefully inform the user *why* the upload failed. They just receive an empty UI or an ambiguous "Failed to process video".

---

## 10. 🧩 Integration Gaps

- **Settings Parsed but Not Fully Respected**
  - The `Auto Best` feature works securely, but if a user explicitly selects `quality="480p"` in their settings, and the video does not have a 480p stream, the bot silently defaults to the highest available stream rather than warning the user.
- **Thumbnail Feature Incomplete**
  - The feature is built into the UI, state machine, and DB, but it will physically fail to apply during the `send_video` API call due to the `file_id` vs `local_path` Pyrogram requirement.

---

## 11. 🧹 Refactoring Recommendations

### High Priority Fixes (Must fix now)
1. **Fix `yt-dlp` Progress Hook Bottleneck**: Reduce Redis cancellation checks to once every 3 seconds instead of every chunk.
2. **Sanitize Filenames**: Strip slashes (`/`, `\`) and null bytes from the User Settings `prefix` and `suffix` before executing `os.rename()`.
3. **Fix Thumbnail Uploads**: Ensure the bot downloads the custom thumbnail `file_id` to a local `.jpg` file before passing it to the Pyrogram upload function.

### Medium Priority (Cleanup + stability)
1. **Refactor `bot/handlers.py`**: Break `button_callback` into modular functions (`process_download`, `process_upload`, `cleanup_task`).
2. **Handle Orphaned Jobs**: Implement a startup script that flushes active locks or resumes uploads for jobs that finished while the bot was offline.

### Low Priority (Nice improvements)
1. **Migrate to Pub/Sub**: Replace the 3-second `asyncio.sleep()` polling loop with Redis Pub/Sub for instant UI updates and lower CPU usage.
2. **Centralize Redis Keys**: Move all raw string keys (e.g., `f"lock:{user_id}"`) into a dedicated `RedisKeys` enum class in `core/redis.py`.

---

## 12. 📁 Suggested Clean Architecture

To truly scale, the bot and the worker should be entirely decoupled, allowing them to run on separate servers (e.g., Bot on Heroku, Worker on a cheap VPS with high storage).

```text
project-root/
│
├── bot/
│   ├── main.py              # Pyrogram entrypoint
│   ├── router.py            # Command routing
│   ├── controllers/         # Logic for downloads, settings, admin
│   ├── views.py             # Pure UI templates (replacing ui.py)
│   └── middlewares.py       # Rate limiting & Auth interception
│
├── worker/                  # Completely decoupled from bot/
│   ├── main.py              # ARQ worker entrypoint
│   ├── engine.py            # yt-dlp execution
│   └── uploader.py          # WORKER handles uploads to Telegram! (New)
│
├── core/
│   ├── redis_client.py      # Connection pools
│   ├── database.py          # MongoDB setup (Future)
│   └── models.py            # Dataclasses/Pydantic models for User Settings
│
└── config.env
```
*Crucial Change:* The worker itself should handle uploading the file to Telegram using a secondary Pyrogram client. This completely eliminates the need for a shared filesystem between the Bot and the Worker.

---

## 13. 🧠 Summary

**Current System Maturity:**
The bot is highly functional, visually polished, and benefits greatly from the recent UI overhauls, Admin Panels, and `yt-dlp` anti-bot bypasses. The distributed ARQ architecture prevents the bot from freezing, which is excellent for production.

**Biggest Risks:**
The primary risks are **Path Traversal** via the unchecked Prefix/Suffix user settings, and **Redis Network Flooding** caused by checking the cancellation status thousands of times per second inside the synchronous `yt-dlp` download hook. Furthermore, if deployed in a true distributed environment, the bot will crash trying to upload files that exist only on the worker's hard drive.

**Next Step Direction:**
A targeted refactor should immediately patch the security risks (path traversal) and performance bottlenecks (progress hook Redis queries). Afterwards, the codebase should be modularized to shrink `bot/handlers.py` and properly finalize the custom thumbnail logic.

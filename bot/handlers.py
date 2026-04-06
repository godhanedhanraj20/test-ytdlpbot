import os
import re
import asyncio
import shutil
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified

from bot.ui import (
    format_size, format_time, make_progress_bar, get_preview_message,
    get_detailed_message, get_completion_summary, get_error_message
)


from services.downloader import extract_video_info, filter_formats
from core.cache import store_format_data, get_format_data, get_progress, set_job_status, cleanup_job_data
from core.limits import acquire_lock, release_lock, request_cancel, is_cancel_requested, check_rate_limit
from core.queue import get_arq_pool
from core.auth import is_user_allowed, add_allowed_user, ADMIN_USER_ID
from core.logger import setup_logger

logger = setup_logger("handlers", "BOT")

URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

REQUIRED_FREE_SPACE = 10 * 1024 * 1024 * 1024
MAX_ALLOWED_SIZE = 4 * 1024 * 1024 * 1024

def check_disk_space() -> bool:
    try:
        total, used, free = shutil.disk_usage("/")
        return free > REQUIRED_FREE_SPACE
    except Exception:
        return True # Fallback if permission denied

def make_progress_bar(percent_str: str) -> str:
    try:
        p = float(percent_str.replace('%', '').strip())
        filled = int(p / 10)
        bar = '█' * filled + '░' * (10 - filled)
        return f"[{bar}] {p:.1f}%"
    except:
        return "[░░░░░░░░░░] 0%"

def make_progress_bar(current: int, total: int) -> str:
    if total == 0:
        return "[░░░░░░░░░░] 0%"
    p = (current / total) * 100
    filled = int(p / 10)
    bar = '█' * filled + '░' * (10 - filled)
    return f"[{bar}] {p:.1f}%"

def _removed_format_speed(speed_bytes: float) -> str:
    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
        if speed_bytes < 1024.0:
            return f"{speed_bytes:.1f} {unit}"
        speed_bytes /= 1024.0
    return f"{speed_bytes:.1f} PB/s"

def register_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start_command(client: Client, message: Message):
        user_id = message.from_user.id
        try:
            allowed = await is_user_allowed(user_id)
            if not allowed:
                await message.reply_text("🚫 You are not allowed to use this bot.")
                return
        except Exception as e:
            logger.error(f"Redis error checking whitelist for {user_id}: {e}")
            await message.reply_text("❌ A database connection error occurred. Please contact the administrator.")
            return

        welcome_msg = (
            "👋 Welcome to the Video Downloader Bot!\n\n"
            "Send me any valid video URL (e.g., YouTube, TikTok, Twitter), "
            "and I will help you download it.\n\n"
            "1️⃣ Send a link\n"
            "2️⃣ Select the format/quality\n"
            "3️⃣ Wait for the download to finish!\n\n"
            "💡 Use /cancel to stop your active download.\n🔄 Use /reset if the bot gets stuck."
        )
        if ADMIN_USER_ID and user_id == ADMIN_USER_ID:
            welcome_msg += "\n\n🔑 **Admin Commands:**\n`/adduser <telegram_id>` - Whitelist a new user."

        await message.reply_text(welcome_msg)

    @app.on_message(filters.command("adduser"))
    async def adduser_command(client: Client, message: Message):
        user_id = message.from_user.id

        if not ADMIN_USER_ID or user_id != ADMIN_USER_ID:
            return

        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("❌ Usage: `/adduser <telegram_id>`")
            return

        try:
            target_id = int(parts[1].strip())
            if await add_allowed_user(target_id):
                await message.reply_text(f"✅ User `{target_id}` has been successfully added to the whitelist.")
            else:
                await message.reply_text(f"ℹ️ User `{target_id}` is already in the whitelist.")
        except ValueError:
            await message.reply_text("❌ Invalid Telegram ID. It must be an integer.")
        except Exception as e:
            logger.error(f"Redis error adding user {target_id}: {e}")
            await message.reply_text("❌ Database error occurred while adding user.")


    @app.on_message(filters.command("reset"))
    async def reset_command(client: Client, message: Message):
        user_id = message.from_user.id
        try:
            await release_lock(user_id)
            await message.reply_text("🔄 Your active lock has been forcefully reset. You may now start a new download.")
            logger.info(f"User {user_id} forcefully reset their lock.")
        except Exception as e:
            logger.error(f"Redis error resetting lock for {user_id}: {e}")
            await message.reply_text("❌ Database error occurred while resetting.")

    @app.on_message(filters.command("cancel"))
    async def cancel_command(client: Client, message: Message):
        user_id = message.from_user.id
        try:
            if not await is_user_allowed(user_id):
                return

            if await request_cancel(user_id):
                logger.info(f"User {user_id} requested cancellation.")
                await message.reply_text("🛑 Cancellation requested. Your active download/upload will stop shortly.")
            else:
                await message.reply_text("❌ You don't have any active downloads to cancel.")
        except Exception as e:
            logger.error(f"Redis error during cancel for {user_id}: {e}")
            await message.reply_text("❌ Database error. Could not process cancellation.")

    @app.on_message(filters.text & ~filters.command(["start", "cancel", "adduser", "reset"]))
    async def handle_message(client: Client, message: Message):
        user_id = message.from_user.id
        try:
            if not await is_user_allowed(user_id):
                await message.reply_text("🚫 You are not allowed to use this bot.")
                return
        except Exception as e:
            logger.error(f"Redis error checking whitelist for {user_id}: {e}")
            await message.reply_text("❌ A database connection error occurred.")
            return

        text = message.text

        if not URL_REGEX.match(text):
            await message.reply_text("❌ Please send a valid HTTP/HTTPS URL.")
            return

        logger.info(f"User {user_id} requested URL: {text}")

        try:
            if not await check_rate_limit(user_id):
                logger.warning(f"User {user_id} hit rate limit.")
                await message.reply_text("⚠️ You reached the hourly limit (5 per 15 min). Try again later.")
                return
        except Exception as e:
            logger.error(f"Redis error checking rate limit for {user_id}: {e}")
            await message.reply_text("❌ A database connection error occurred.")
            return

        if not check_disk_space():
            logger.error("Server disk space is low.")
            await message.reply_text("⚠️ Server disk space is low. Please try again later.")
            return

        processing_msg = await message.reply_text("🔄 Extracting video information...")

        try:
            info = await extract_video_info(text)
            filtered_formats = filter_formats(info.get('formats', []))

            if not filtered_formats:
                await processing_msg.edit_text("❌ No suitable formats found.")
                return

            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)

            keyboard = []
            row = []
            for i, f in enumerate(filtered_formats):
                size_bytes = f['size_bytes']
                f_type = f.get('type', 'video')
                emoji = "🎥" if f_type == 'video' else "🎵"

                # Highlight best video format (usually the first one since it's sorted by resolution)
                recommended = " ⭐" if f_type == 'video' and i == 0 else ""
                btn_text = f"{emoji} {f['quality']} {f['ext'].upper()} – {f['size_str']}{recommended}"

                short_id = await store_format_data(text, f['format_id'], size_bytes, title)
                callback_data = f"dl_{short_id}"

                row.append(InlineKeyboardButton(btn_text, callback_data=callback_data))
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            if row:
                keyboard.append(row)

            # Add Cancel button
            keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_selection")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.info(f"Successfully extracted {len(filtered_formats)} formats for user {user_id}.")

            preview_text = get_preview_message(title, duration)
            await processing_msg.edit_text(
                preview_text,
                reply_markup=reply_markup
            )

        except ValueError as e:
            logger.warning(f"Extraction failed for user {user_id}: {e}")
            await processing_msg.edit_text(f"❌ Could not extract video info.\n\nError: {e}")
        except Exception as e:
            logger.error(f"Error extracting video for user {user_id}: {e}", exc_info=True)
            await processing_msg.edit_text("❌ An unexpected error occurred while processing the URL.")



    @app.on_callback_query(filters.regex(r"^cancel_job$"))
    async def cancel_job_callback(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        from core.limits import request_cancel
        await request_cancel(user_id)
        await callback_query.answer("🛑 Cancellation requested...", show_alert=True)

    @app.on_callback_query(filters.regex(r"^refresh_job$"))
    async def refresh_job_callback(client: Client, callback_query: CallbackQuery):
        await callback_query.answer("🔄 Refreshing status...")

    @app.on_callback_query(filters.regex(r"^cancel_selection$"))
    async def cancel_selection_callback(client: Client, callback_query: CallbackQuery):
        await callback_query.edit_message_text("❌ Operation cancelled.")

    @app.on_callback_query(filters.regex(r"^dl_"))
    async def button_callback(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        try:
            if not await is_user_allowed(user_id):
                await callback_query.answer("🚫 You are not allowed to use this bot.", show_alert=True)
                return
        except Exception as e:
            logger.error(f"Redis error checking whitelist: {e}")
            await callback_query.answer("❌ Database connection error.", show_alert=True)
            return

        parts = callback_query.data.split("_")

        if len(parts) < 2:
            await callback_query.answer("Invalid request.", show_alert=True)
            return

        short_id = parts[1]

        try:
            format_data = await get_format_data(short_id)
        except Exception as e:
            logger.error(f"Redis error getting format data: {e}")
            await callback_query.answer("❌ Database error retrieving format data.", show_alert=True)
            return

        if not format_data:
            await callback_query.edit_message_text(text="❌ Session expired. Please send the link again.")
            return

        url = format_data["url"]
        format_id = format_data["format_id"]
        size_bytes = format_data["size_bytes"]

        if size_bytes > MAX_ALLOWED_SIZE:
            await callback_query.answer("❌ File is too large for Telegram to handle (>4GB).", show_alert=True)
            return

        if size_bytes > 2 * 1024 * 1024 * 1024:
            await callback_query.answer("⚠️ File is over 2GB. Requires Premium Userbot.", show_alert=False)

        try:
            if not await acquire_lock(user_id):
                await callback_query.answer("⚠️ You already have a download in progress. Please wait.", show_alert=True)
                return
        except Exception as e:
            logger.error(f"Redis error acquiring lock: {e}")
            await callback_query.answer("❌ Database error acquiring lock.", show_alert=True)
            return

        if not check_disk_space():
            try:
                await release_lock(user_id)
            except:
                pass
            await callback_query.answer("⚠️ Server disk space is low. Please try again later.", show_alert=True)
            return

        await callback_query.edit_message_text(text="⏳ Enqueueing download...")
        logger.info(f"User {user_id} enqueuing download for format {format_id}.")

        try:
            # Wrap get_arq_pool securely to catch ConnectionErrors from ARQ
            redis_pool = await get_arq_pool()
            job = await redis_pool.enqueue_job('download_task', url, format_id, user_id)

            if not job:
                await release_lock(user_id)
                logger.error(f"Failed to enqueue task for user {user_id}.")
                await callback_query.edit_message_text(text="❌ Failed to enqueue task. Please try again.")
                return

            await set_job_status(job.job_id, user_id, "queued")
        except Exception as e:
            logger.error(f"Redis ARQ Error during enqueue: {e}", exc_info=True)
            try:
                await release_lock(user_id)
            except:
                pass
            await callback_query.edit_message_text(text="❌ Failed to connect to background queue. Ensure Redis is properly configured.")
            return

        file_path = None
        try:
            start_time = time.time()
            file_path = None
            user_name = callback_query.from_user.first_name or "User"
            title = format_data.get("title", "Unknown Video")

            while True:
                if await is_cancel_requested(user_id):
                    await callback_query.edit_message_text(text="🛑 Cancellation requested. Waiting for worker to stop...")

                status = await job.status()
                if status == status.complete:
                    result = await job.result()
                    if result['status'] == 'success':
                        file_path = result['file_path']
                        break
                    elif result['status'] == 'cancelled':
                        await callback_query.edit_message_text(text="🛑 Task cancelled by user.")
                        return
                    elif result['status'] == 'error':
                        error_msg = result.get('message', 'Unknown Error')
                        logger.warning(f"Worker returned structured error for user {user_id}: {error_msg}")
                        await callback_query.edit_message_text(text=get_error_message(error_msg))
                        return
                    else:
                        raise Exception("Unknown worker state.")

                elapsed = int(time.time() - start_time)

                if status == status.queued:
                    try:
                        redis = await get_arq_pool()
                        queued = len(await redis.queued_jobs())
                        msg_text = get_detailed_message(
                            title, "Queued", 0.0, queued, 0, "N/A", 0, elapsed, user_name, user_id
                        )
                        await callback_query.edit_message_text(
                            text=msg_text,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔄 Refresh", callback_data="refresh_job"),
                                InlineKeyboardButton("❌ Cancel", callback_data="cancel_job")
                            ]])
                        )
                    except MessageNotModified:
                        pass
                    except Exception:
                        pass
                else:
                    progress_data = await get_progress(job.job_id)
                    if progress_data and not await is_cancel_requested(user_id):
                        try:
                            percent_str = progress_data['percent'].replace('%', '').strip()
                            percent = float(percent_str) if percent_str else 0.0
                        except:
                            percent = 0.0

                        msg_text = get_detailed_message(
                            title,
                            "Downloading",
                            percent,
                            progress_data.get('downloaded', 0),
                            progress_data.get('total', 0),
                            progress_data.get('speed', 'N/A'),
                            progress_data.get('eta', 0),
                            elapsed,
                            user_name,
                            user_id
                        )
                        try:
                            await callback_query.edit_message_text(
                                msg_text,
                                reply_markup=InlineKeyboardMarkup([[
                                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_job")
                                ]])
                            )
                        except MessageNotModified:
                            pass
                        except Exception:
                            pass

                await asyncio.sleep(3)

            logger.info(f"Upload starting for user {user_id}.")
            await set_job_status(job.job_id, user_id, "uploading")

            try:
                file_size = os.path.getsize(file_path)
            except:
                file_size = 0

            elapsed = int(time.time() - start_time)
            msg_text = get_detailed_message(
                title, "Uploading", 0.0, 0, file_size, "N/A", 0, elapsed, user_name, user_id
            )
            await callback_query.edit_message_text(
                text=msg_text,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_job")
                ]])
            )

            last_update_time = [time.time()]
            last_current = [0]

            async def upload_progress(current, total):
                if await is_cancel_requested(user_id):
                    logger.info(f"User {user_id} cancelled upload.")
                    client.stop_transmission()

                now = time.time()
                if now - last_update_time[0] > 3:
                    speed_bytes = (current - last_current[0]) / (now - last_update_time[0])
                    last_update_time[0] = now
                    last_current[0] = current

                    percent = (current / total * 100) if total else 0.0
                    eta = int((total - current) / speed_bytes) if speed_bytes > 0 else 0
                    speed_str = format_size(speed_bytes) + '/s'
                    elapsed_upload = int(now - start_time)

                    msg_text = get_detailed_message(
                        title, "Uploading", percent, current, total, speed_str, eta, elapsed_upload, user_name, user_id
                    )

                    try:
                        await callback_query.edit_message_text(
                            text=msg_text,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("❌ Cancel", callback_data="cancel_job")
                            ]])
                        )
                    except MessageNotModified:
                        pass
                    except Exception:
                        pass

            if file_size > 1024 * 1024 * 1024:
                try:
                    await client.send_message(
                        chat_id=callback_query.message.chat.id,
                        text="⚠️ File is larger than 1GB. Upload may take a while!"
                    )
                except:
                    pass

            await asyncio.wait_for(
                client.send_document(
                    chat_id=callback_query.message.chat.id,
                    document=file_path,
                    caption=f"🎬 **{title}**",
                    progress=upload_progress
                ),
                timeout=600
            )

            logger.info(f"Upload completed for user {user_id}.")
            total_time = int(time.time() - start_time)
            await callback_query.edit_message_text(text=get_completion_summary(total_time, file_size, title))

        except asyncio.TimeoutError:
            logger.error(f"Upload timed out (10 min limit) for user {user_id}.")
            await callback_query.edit_message_text(text="❌ Upload timed out. Please try a smaller format.")
        except Exception as e:
            if "StopTransmission" in str(e) or "User requested cancellation" in str(e) or "cancelled" in str(e).lower():
                await callback_query.edit_message_text(text="🛑 Task cancelled by user.")
            else:
                logger.error(f"Error handling job for user {user_id}: {e}", exc_info=True)
                await client.send_message(
                    chat_id=callback_query.message.chat.id,
                    text="❌ Failed to process video due to an unexpected error."
                )
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up file {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to delete {file_path}: {cleanup_error}")

            if 'job' in locals() and job:
                try:
                    await cleanup_job_data(job.job_id)
                except:
                    pass

            try:
                await release_lock(user_id)
            except:
                pass

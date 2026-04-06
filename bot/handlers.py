import os
import re
import logging
import asyncio
import shutil
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified

from services.downloader import extract_video_info, download_video, filter_formats, CancelledError
from core.cache import store_format_data, get_format_data
from core.limits import acquire_lock, release_lock, request_cancel, is_cancel_requested
from core.queue import download_queue

logger = logging.getLogger(__name__)

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
    total, used, free = shutil.disk_usage("/")
    return free > REQUIRED_FREE_SPACE

def make_progress_bar(percent_str: str) -> str:
    try:
        # percent_str usually looks like " 45.2%" or "45%"
        p = float(percent_str.replace('%', '').strip())
        filled = int(p / 10)
        bar = '█' * filled + '░' * (10 - filled)
        return f"[{bar}] {p:.1f}%"
    except:
        return "[░░░░░░░░░░] 0%"

def make_upload_progress_bar(current: int, total: int) -> str:
    if total == 0:
        return "[░░░░░░░░░░] 0%"
    p = (current / total) * 100
    filled = int(p / 10)
    bar = '█' * filled + '░' * (10 - filled)
    return f"[{bar}] {p:.1f}%"

def format_speed(speed_bytes: float) -> str:
    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
        if speed_bytes < 1024.0:
            return f"{speed_bytes:.1f} {unit}"
        speed_bytes /= 1024.0
    return f"{speed_bytes:.1f} PB/s"

def register_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start_command(client: Client, message: Message):
        welcome_msg = (
            "👋 Welcome to the Video Downloader Bot!\n\n"
            "Send me any valid video URL (e.g., YouTube, TikTok, Twitter), "
            "and I will help you download it.\n\n"
            "1️⃣ Send a link\n"
            "2️⃣ Select the format/quality\n"
            "3️⃣ Wait for the download to finish!\n\n"
            "💡 Use /cancel to stop your active download."
        )
        await message.reply_text(welcome_msg)

    @app.on_message(filters.command("cancel"))
    async def cancel_command(client: Client, message: Message):
        user_id = message.from_user.id
        if request_cancel(user_id):
            await message.reply_text("🛑 Cancellation requested. Your active download/upload will stop shortly.")
        else:
            await message.reply_text("❌ You don't have any active downloads to cancel.")

    @app.on_message(filters.text & ~filters.command(["start", "cancel"]))
    async def handle_message(client: Client, message: Message):
        text = message.text

        if not URL_REGEX.match(text):
            await message.reply_text("❌ Please send a valid HTTP/HTTPS URL.")
            return

        if not check_disk_space():
            await message.reply_text("⚠️ Server disk space is low. Please try again later.")
            return

        processing_msg = await message.reply_text("🔄 Extracting video information...")

        try:
            info = await extract_video_info(text)

            title = info.get('title', 'Unknown Title')
            formats = info.get('formats', [])

            filtered_formats = filter_formats(formats)

            if not filtered_formats:
                await processing_msg.edit_text("❌ No supported formats found for this video.")
                return

            keyboard = []
            row = []
            for f in filtered_formats:
                format_id = f['format_id']
                size_bytes = f['size_bytes']
                f_type = f.get('type', 'video')

                # Smart UI Emoji
                emoji = "🎥" if f_type == 'video' else "🎵"
                btn_text = f"{emoji} {f['quality']} {f['ext'].upper()} – {f['size_str']}"

                short_id = store_format_data(text, format_id, size_bytes)
                callback_data = f"dl_{short_id}"

                row.append(InlineKeyboardButton(btn_text, callback_data=callback_data))

                if len(row) == 2:
                    keyboard.append(row)
                    row = []

            if row:
                keyboard.append(row)

            reply_markup = InlineKeyboardMarkup(keyboard)

            await processing_msg.edit_text(
                f"🎬 **{title}**\n\nSelect a format to download:",
                reply_markup=reply_markup
            )

        except ValueError as e:
            await processing_msg.edit_text(f"❌ Could not extract video info.\n\nError: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await processing_msg.edit_text("❌ An unexpected error occurred while processing the URL.")

    @app.on_callback_query(filters.regex(r"^dl_"))
    async def button_callback(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        data = callback_query.data
        parts = data.split("_")

        if len(parts) < 2:
            await callback_query.answer("Invalid request.", show_alert=True)
            return

        short_id = parts[1]
        format_data = get_format_data(short_id)

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

        if not acquire_lock(user_id):
            await callback_query.answer("⚠️ You already have a download in progress. Please wait.", show_alert=True)
            return

        if not check_disk_space():
            release_lock(user_id)
            await callback_query.answer("⚠️ Server disk space is low. Please try again later.", show_alert=True)
            return

        await callback_query.edit_message_text(text="⏳ Queued for download... Please wait.")

        async def process_task():
            file_path = None
            try:
                if is_cancel_requested(user_id):
                    raise CancelledError("Cancelled before start.")

                await callback_query.edit_message_text(text="📥 Downloading video...\n\n[░░░░░░░░░░] 0%")

                async def download_progress_hook(percent: str, speed: str):
                    try:
                        bar = make_progress_bar(percent)
                        await callback_query.edit_message_text(f"📥 Downloading video...\n\n{bar}\nSpeed: {speed}")
                    except MessageNotModified:
                        pass
                    except Exception as e:
                        pass

                file_path = await download_video(url, format_id, user_id, download_progress_hook)

                if is_cancel_requested(user_id):
                    raise CancelledError("Cancelled after download.")

                await callback_query.edit_message_text(text="⬆️ Uploading to Telegram...\n\n[░░░░░░░░░░] 0%")

                # Upload progress state
                last_update_time = [time.time()]
                last_current = [0]

                async def upload_progress(current, total):
                    if is_cancel_requested(user_id):
                        client.stop_transmission()

                    now = time.time()
                    if now - last_update_time[0] > 3:
                        speed_bytes = (current - last_current[0]) / (now - last_update_time[0])
                        last_update_time[0] = now
                        last_current[0] = current

                        speed_str = format_speed(speed_bytes)
                        bar = make_upload_progress_bar(current, total)

                        try:
                            await callback_query.edit_message_text(
                                f"⬆️ Uploading to Telegram...\n\n{bar}\nSpeed: {speed_str}"
                            )
                        except MessageNotModified:
                            pass
                        except Exception:
                            pass

                await client.send_document(
                    chat_id=callback_query.message.chat.id,
                    document=file_path,
                    caption="Here is your video!",
                    progress=upload_progress
                )

                await callback_query.edit_message_text(text="✅ Finished!")

            except CancelledError:
                await callback_query.edit_message_text(text="🛑 Task cancelled by user.")
            except Exception as e:
                # Catch Pyrogram StopTransmission thrown by stop_transmission()
                if "StopTransmission" in str(e) or "User requested cancellation" in str(e):
                    await callback_query.edit_message_text(text="🛑 Task cancelled by user.")
                else:
                    logger.error(f"Error downloading/uploading: {e}", exc_info=True)
                    await client.send_message(
                        chat_id=callback_query.message.chat.id,
                        text=f"❌ Failed to process video. Error: {str(e)}"
                    )
            finally:
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as cleanup_error:
                        logger.error(f"Failed to delete {file_path}: {cleanup_error}")
                release_lock(user_id)

        await download_queue.put(process_task)

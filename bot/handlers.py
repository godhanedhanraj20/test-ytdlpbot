import os
import re
import logging
import asyncio
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import MessageNotModified

from services.downloader import extract_video_info, download_video, filter_formats
from core.cache import store_format_data, get_format_data
from core.limits import acquire_lock, release_lock
from core.queue import download_queue

logger = logging.getLogger(__name__)

URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://' # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
    r'localhost|' #localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
    r'(?::\d+)?' # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

# 10 GB required free space
REQUIRED_FREE_SPACE = 10 * 1024 * 1024 * 1024
MAX_ALLOWED_SIZE = 4 * 1024 * 1024 * 1024 # 4GB hard max for premium userbot

def check_disk_space() -> bool:
    total, used, free = shutil.disk_usage("/")
    return free > REQUIRED_FREE_SPACE

def register_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start_command(client: Client, message: Message):
        welcome_msg = (
            "👋 Welcome to the Video Downloader Bot!\n\n"
            "Send me any valid video URL (e.g., YouTube, TikTok, Twitter), "
            "and I will help you download it.\n\n"
            "1️⃣ Send a link\n"
            "2️⃣ Select the format/quality\n"
            "3️⃣ Wait for the download to finish!"
        )
        await message.reply_text(welcome_msg)

    @app.on_message(filters.text & ~filters.command("start"))
    async def handle_message(client: Client, message: Message):
        text = message.text
        user_id = message.from_user.id

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
                btn_text = f"{f['quality']} | {f['ext']} | {f['size_str']}"

                # Store in cache and get short ID
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
            await processing_msg.edit_text(f"❌ Could not extract video info. Are you sure the URL is supported?\n\nError: {e}")
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
            # Inform user it's over 2GB
            await callback_query.answer("⚠️ File is over 2GB. Requires Premium Userbot.", show_alert=False)

        if not acquire_lock(user_id):
            await callback_query.answer("⚠️ You already have a download in progress. Please wait.", show_alert=True)
            return

        if not check_disk_space():
            release_lock(user_id)
            await callback_query.answer("⚠️ Server disk space is low. Please try again later.", show_alert=True)
            return

        await callback_query.edit_message_text(text="⏳ Queued for download... Please wait.")

        # Define the actual task to be processed by the worker queue
        async def process_task():
            try:
                await callback_query.edit_message_text(text="⏳ Downloading video...\n\nProgress: 0%")

                async def progress_hook(percent: str, speed: str):
                    try:
                        await callback_query.edit_message_text(f"⏳ Downloading video...\n\nProgress: {percent}\nSpeed: {speed}")
                    except MessageNotModified:
                        pass
                    except Exception as e:
                        logger.warning(f"Error updating progress: {e}")

                file_path = None
                try:
                    file_path = await download_video(url, format_id, progress_hook)

                    await callback_query.edit_message_text(text="⬆️ Download complete. Uploading to Telegram...")

                    # Upload using Pyrogram
                    await client.send_document(
                        chat_id=callback_query.message.chat.id,
                        document=file_path,
                        caption="Here is your video!"
                    )

                    await callback_query.edit_message_text(text="✅ Finished!")

                except Exception as e:
                    logger.error(f"Error downloading/uploading: {e}", exc_info=True)
                    await client.send_message(
                        chat_id=callback_query.message.chat.id,
                        text=f"❌ Failed to process video. Error: {str(e)}"
                    )
                finally:
                    # Clean up local file
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as cleanup_error:
                            logger.error(f"Failed to delete {file_path}: {cleanup_error}")
            finally:
                # Always release the user lock when task is done or fails
                release_lock(user_id)

        # Push to the queue
        await download_queue.put(process_task)

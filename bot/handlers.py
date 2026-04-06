import os
import re
import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from services.downloader import extract_video_info, download_video, filter_formats

logger = logging.getLogger(__name__)

URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://' # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
    r'localhost|' #localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
    r'(?::\d+)?' # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

# In-memory storage for URL caching since CallbackQuery has a 64-byte payload limit
url_cache = {}

def register_handlers(app: Client):
    @app.on_message(filters.command("start"))
    async def start_command(client: Client, message: Message):
        """Send a message when the command /start is issued."""
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
        """Handles incoming text messages, checking for URLs."""
        text = message.text

        if not URL_REGEX.match(text):
            await message.reply_text("❌ Please send a valid HTTP/HTTPS URL.")
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
                btn_text = f"{f['quality']} | {f['ext']} | {f['size_str']}"
                callback_data = f"dl_{format_id}_{message.id}"

                row.append(InlineKeyboardButton(btn_text, callback_data=callback_data))

                if len(row) == 2:
                    keyboard.append(row)
                    row = []

            if row:
                keyboard.append(row)

            reply_markup = InlineKeyboardMarkup(keyboard)

            # Store URL in cache using message ID as key
            url_cache[message.id] = text

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
        """Parses the CallbackQuery and updates the message text."""
        data = callback_query.data
        parts = data.split("_")

        if len(parts) < 3:
            await callback_query.answer("Invalid request.", show_alert=True)
            return

        format_id = parts[1]
        msg_id = int(parts[2])

        url = url_cache.get(msg_id)

        if not url:
            await callback_query.edit_message_text(text="❌ Session expired. Please send the link again.")
            return

        await callback_query.edit_message_text(text="⏳ Downloading video... Please wait (this might take a while).")

        file_path = None
        try:
            file_path = await download_video(url, format_id)

            await callback_query.edit_message_text(text="⬆️ Download complete. Uploading to Telegram...")

            # Upload using Pyrogram (supports up to 2GB normally, 4GB with Premium Userbot)
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
                text=f"❌ Failed to download or upload the video. Error: {str(e)}"
            )
        finally:
            # Always clean up the file
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as cleanup_error:
                    logger.error(f"Failed to delete {file_path}: {cleanup_error}")

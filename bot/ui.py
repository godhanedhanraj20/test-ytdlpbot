import math
import time
import psutil
import shutil

START_TIME = time.time()

def format_size(bytes_size: int) -> str:
    if not bytes_size or bytes_size == 0:
        return "0B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.2f}{unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f}PB"

def format_time(seconds: int) -> str:
    if not seconds:
        return "0s"
    seconds = int(seconds)
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if mins > 0:
        parts.append(f"{mins}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return "".join(parts)

def make_progress_bar(percent_val: float, width: int = 10) -> str:
    filled = int(round(percent_val / 100 * width))
    if filled > width:
        filled = width
    elif filled < 0:
        filled = 0
    empty = width - filled
    return "✦" * filled + "✧" * empty

def get_sys_stats() -> dict:
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    total, used, free = shutil.disk_usage("/")
    free_str = format_size(free)
    disk_percent = (used / total) * 100

    uptime = time.time() - START_TIME

    return {
        "cpu": cpu,
        "ram": ram,
        "free_disk": free_str,
        "disk_percent": disk_percent,
        "uptime": format_time(uptime)
    }

def get_preview_message(title: str, duration: int) -> str:
    duration_str = format_time(duration) if duration else "Unknown"
    return (
        f"🎬 **{title}**\n"
        f"⏱ Duration: {duration_str}\n\n"
        "Select a format to download:"
    )

def get_detailed_message(
    title: str,
    status: str,
    percent: float,
    processed: int,
    total: int,
    speed: str,
    eta: int,
    elapsed: int,
    user_name: str,
    user_id: int
) -> str:
    bar = make_progress_bar(percent)
    processed_str = format_size(processed)
    total_str = format_size(total) if total else "?"

    stats = get_sys_stats()

    msg = f"**{title}**\n"
    msg += f"┃ 〖{bar}〗 {percent:.2f}%\n"
    if status == "Queued":
        msg += f"┠ Status: ⏳ Queued | Pos: {processed}\n"
    else:
        msg += f"┠ Processed: {processed_str} of {total_str}\n"
        status_emoji = "📥 Download" if status == "Downloading" else "📤 Upload"
        msg += f"┠ Status: {status_emoji} | ETA: {format_time(eta)}\n"
        msg += f"┠ Speed: {speed} | Elapsed: {format_time(elapsed)}\n"

    msg += f"┠ Engine: Obsidian Media Node | Pyrogram\n"
    msg += f"┠ User: {user_name} | ID: {user_id}\n"
    msg += f"┖ /cancel\n\n"

    msg += f"⌬ Bot Stats\n"
    msg += f"┠ CPU: {stats['cpu']}% | F: {stats['free_disk']} [{stats['disk_percent']:.1f}%]\n"
    msg += f"┖ RAM: {stats['ram']}% | UPTIME: {stats['uptime']}"

    return msg

def get_completion_summary(total_time: int, file_size: int, title: str) -> str:
    return (
        f"✅ **Obsidian Node Complete**\n🎬 {title}\n\n"
        f"⏱ Total time: {format_time(total_time)}\n"
        f"📦 Size: {format_size(file_size)}"
    )

def get_error_message(reason: str) -> str:
    return (
        f"❌ **Obsidian Node Error**\n"
        f"Reason: {reason}"
    )

def get_download_progress_message(*args, **kwargs):
    pass # Replaced by detailed message

def get_upload_progress_message(*args, **kwargs):
    pass # Replaced by detailed message

def get_queued_message(*args, **kwargs):
    pass # Replaced by detailed message



def get_admin_panel(users: int, active: int, queued: int, paused: bool) -> str:
    status = "⛔ PAUSED" if paused else "▶️ ACTIVE"
    return (
        f"⚙️ **Obsidian Media Node Control Panel**\n\n"
        f"🚦 Status: {status}\n"
        f"👥 Total Users: {users}\n"
        f"📥 Active Jobs: {active}\n"
        f"📦 Queue Size: {queued}\n"
    )


def get_user_settings_panel(settings: dict) -> str:
    mode = "🎬 Video" if settings.get("mode") == "video" else "🎵 Audio"
    send_as = "📺 Media" if settings.get("send_as") == "media" else "📄 Document"
    quality = "🤔 Ask Every Time" if settings.get("quality") == "ask" else f"🎥 {str(settings.get('quality')).capitalize()}"
    if settings.get('auto_best'):
        quality = "⭐ Auto Best"

    thumbnail = "✅ Set" if settings.get("thumbnail") else "❌ Not Set"
    prefix = settings.get("prefix") or "None"
    suffix = settings.get("suffix") or "None"

    return (
        f"⚙️ **User Settings**\n\n"
        f"🎬 **Mode:** {mode}\n"
        f"📄 **Send As:** {send_as}\n"
        f"🎥 **Quality:** {quality}\n"
        f"🖼 **Thumbnail:** {thumbnail}\n"
        f"✏️ **Prefix:** {prefix}\n"
        f"✏️ **Suffix:** {suffix}\n\n"
        f"Select an option to modify:"
    )

def get_user_settings_keyboard(settings: dict):
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Toggle states
    mode_btn = "🎵 Audio" if settings.get("mode") == "audio" else "🎬 Video"
    send_as_btn = "📄 Doc" if settings.get("send_as") == "document" else "📺 Media"
    auto_best_btn = "⭐ Auto Best: ON" if settings.get("auto_best") else "⭐ Auto Best: OFF"

    keyboard = [
        [InlineKeyboardButton(f"Mode: {mode_btn}", callback_data="us_mode"), InlineKeyboardButton(f"Send As: {send_as_btn}", callback_data="us_send")],
        [InlineKeyboardButton("🎥 Quality Preference", callback_data="us_quality")],
        [InlineKeyboardButton(auto_best_btn, callback_data="us_autobest")],
        [InlineKeyboardButton("🖼 Custom Thumbnail", callback_data="us_thumb"), InlineKeyboardButton("🗑 Clear Thumb", callback_data="us_clear_thumb")],
        [InlineKeyboardButton("✏️ Set Prefix", callback_data="us_prefix"), InlineKeyboardButton("✏️ Set Suffix", callback_data="us_suffix")],
        [InlineKeyboardButton("🗑 Clear Tags", callback_data="us_clear_tags"), InlineKeyboardButton("❌ Close", callback_data="us_close")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_quality_settings_keyboard():
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = [
        [InlineKeyboardButton("🤔 Ask Every Time", callback_data="us_q_ask")],
        [InlineKeyboardButton("⭐ Best Available", callback_data="us_q_best")],
        [InlineKeyboardButton("🎥 1080p", callback_data="us_q_1080p"), InlineKeyboardButton("🎥 720p", callback_data="us_q_720p")],
        [InlineKeyboardButton("🎥 480p", callback_data="us_q_480p"), InlineKeyboardButton("🎥 360p", callback_data="us_q_360p")],
        [InlineKeyboardButton("⬅️ Back to Settings", callback_data="us_back")]
    ]
    return InlineKeyboardMarkup(keyboard)

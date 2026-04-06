import math

def format_size(bytes_size: int) -> str:
    if not bytes_size or bytes_size == 0:
        return "Unknown Size"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"

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

    return " ".join(parts)

def make_progress_bar(percent_val: float, width: int = 10) -> str:
    filled = int(round(percent_val / 100 * width))
    if filled > width:
        filled = width
    elif filled < 0:
        filled = 0
    empty = width - filled
    return "█" * filled + "░" * empty

def get_preview_message(title: str, duration: int) -> str:
    duration_str = format_time(duration) if duration else "Unknown"
    return (
        f"🎬 **{title}**\n"
        f"⏱ Duration: {duration_str}\n\n"
        "Select a format to download:"
    )

def get_download_progress_message(percent: float, speed: str, downloaded: int, total: int, eta: int) -> str:
    bar = make_progress_bar(percent)
    dl_str = format_size(downloaded) if downloaded else "?"
    total_str = format_size(total) if total else "?"
    eta_str = format_time(eta) if eta is not None else "Unknown"

    return (
        f"📥 **Downloading...**\n\n"
        f"{bar} {percent:.1f}%\n\n"
        f"⚡ Speed: {speed}\n"
        f"📦 {dl_str} / {total_str}\n"
        f"⏱ ETA: {eta_str}"
    )

def get_upload_progress_message(percent: float, speed_bytes: float) -> str:
    bar = make_progress_bar(percent)
    speed_str = format_size(int(speed_bytes)) + "/s" if speed_bytes else "0 B/s"

    return (
        f"📤 **Uploading...**\n\n"
        f"{bar} {percent:.1f}%\n\n"
        f"⚡ Speed: {speed_str}"
    )

def get_queued_message(position: int) -> str:
    return (
        f"⏳ **Added to queue**\n"
        f"Position: #{position}"
    )

def get_completion_summary(total_time: int, file_size: int) -> str:
    return (
        f"✅ **Download complete**\n\n"
        f"⏱ Total time: {format_time(total_time)}\n"
        f"📦 Size: {format_size(file_size)}"
    )

def get_error_message(reason: str) -> str:
    return (
        f"❌ **Download failed**\n"
        f"Reason: {reason}"
    )

import re

with open("services/downloader.py", "r") as f:
    content = f.read()

# Add shutil import if missing
if "import shutil" not in content:
    content = content.replace("import os", "import os\nimport shutil")

# Add FFmpegMissingError exception
ffmpeg_error = """class FFmpegMissingError(Exception):
    pass

class CancelledError(Exception):"""

content = content.replace("class CancelledError(Exception):", ffmpeg_error)

# Update filter_formats
old_filter = """
        if is_video:
            item['type'] = 'video'
            if not is_audio:
                # Video only (Muted)
                item['quality'] = f"{f.get('height', '?')}p 🔇"
            else:
                # Video + Audio
                item['quality'] = f"{f.get('height', '?')}p 🔊"
            video_formats.append(item)
        elif is_audio:
            item['type'] = 'audio'
            item['quality'] = "Audio 🎵"
            audio_formats.append(item)
"""

new_filter = """
        if is_video:
            item['type'] = 'video'
            if not is_audio:
                # Video only
                item['quality'] = f"{f.get('height', '?')}p (video only, will merge audio)"
            else:
                # Video + Audio
                item['quality'] = f"{f.get('height', '?')}p (with audio)"
            video_formats.append(item)
        elif is_audio:
            item['type'] = 'audio'
            item['quality'] = "Audio"
            audio_formats.append(item)
"""
content = content.replace(old_filter.strip(), new_filter.strip())

# Add FFmpeg check to download_video
ffmpeg_check = """
async def download_video(url: str, format_id: str, user_id: int, progress_message_func=None) -> str:
    # Ensure system supports merging
    if not shutil.which("ffmpeg"):
        logger.error("ffmpeg is not installed on the server.")
        raise FFmpegMissingError("⚠️ Audio merging not supported on server. ffmpeg is missing.")

    last_update_time = [time.time()]
"""

content = re.sub(r"async def download_video\(.*?\).*?    last_update_time = \[time\.time\(\)\]", ffmpeg_check.strip("\n"), content, flags=re.DOTALL)

with open("services/downloader.py", "w") as f:
    f.write(content)

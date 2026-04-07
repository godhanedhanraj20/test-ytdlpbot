import re

with open("bot/handlers.py", "r") as f:
    content = f.read()

# Since I removed the emojis from filter_formats 'quality' string, I should ensure handlers prepend the right one.
# It does: `emoji = "🎥" if f_type == 'video' else "🎵"`
# So it becomes `🎥 1080p (video only, will merge audio) MP4 - 15MB ⭐`
# Wait, the user's example was exactly:
# 🎥 1080p (video only, will merge audio)
# 🎥 720p (with audio)
# 🎵 Audio MP3
# My current format string is:
# btn_text = f"{emoji} {f['quality']} {f['ext'].upper()} – {f['size_str']}{recommended}"
# Which generates: `🎥 1080p (video only, will merge audio) MP4 – 15.0MB`
# This matches perfectly!

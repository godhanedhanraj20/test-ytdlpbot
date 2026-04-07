import re

with open("services/downloader.py", "r") as f:
    content = f.read()

# Remove forced extractor_args for android/ios which fails without PO token
content = re.sub(r"        'extractor_args': \{\n            'youtube': \{\n                'player_client': \['android', 'ios'\]\n            \}\n        \},", "", content)

# Change extract error message
new_extract_error = """
        if "sign in" in error_str or "login" in error_str or "bot" in error_str:
            raise ValueError("Video is restricted or blocked by YouTube anti-bot checks.\\n\\n**How to bypass:**\\n1. Try a different video link.\\n2. Deploy this bot on a residential IP or VPS (Google Cloud IPs are often blocked).\\n3. (Advanced) Configure yt-dlp with `--cookies` in the source code.")
"""
content = re.sub(r"        if \"sign in\" in error_str or \"login\" in error_str or \"bot\" in error_str:\n            raise ValueError\(\"Video requires login, is age-restricted, or blocked by anti-bot checks\.\"\)", new_extract_error.strip("\n"), content)

with open("services/downloader.py", "w") as f:
    f.write(content)

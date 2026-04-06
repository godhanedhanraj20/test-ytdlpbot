import os
import uuid
import asyncio
from yt_dlp import YoutubeDL
from typing import Dict, Any, List

DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')

# Ensure download directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def _extract_info_sync(url: str) -> Dict[str, Any]:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

async def extract_video_info(url: str) -> Dict[str, Any]:
    """
    Extracts video formats and metadata using yt-dlp without downloading.
    Runs asynchronously to not block the main event loop.
    """
    try:
        result = await asyncio.to_thread(_extract_info_sync, url)
        return result
    except Exception as e:
        raise ValueError(f"Failed to extract info: {str(e)}")

def _download_video_sync(url: str, format_id: str) -> str:
    # Generate a unique filename using UUID to avoid collisions
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f'%(title)s_{unique_id}.%(ext)s')

    ydl_opts = {
        'format': format_id,
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # yt-dlp replaces characters in the actual filename, so we must ask it for the true filename
        filename = ydl.prepare_filename(info)

        # Sometimes format selection results in merging files, changing extension
        # If the expected file doesn't exist, search the dir for matching unique ID
        if not os.path.exists(filename):
             for file in os.listdir(DOWNLOAD_DIR):
                 if unique_id in file:
                     return os.path.join(DOWNLOAD_DIR, file)

        return filename

async def download_video(url: str, format_id: str) -> str:
    """
    Downloads the selected video format.
    Returns the absolute file path of the downloaded video.
    """
    try:
        file_path = await asyncio.to_thread(_download_video_sync, url, format_id)
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("Downloaded file could not be found.")
        return file_path
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")

def format_size(bytes_size: int) -> str:
    if not bytes_size:
        return "Unknown Size"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} PB"

def filter_formats(formats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters and formats the yt-dlp format list for presentation.
    """
    valid_formats = []
    for f in formats:
        # We generally want video+audio formats or good audio/video formats to offer
        # To avoid spamming 100 buttons, let's filter intelligently.
        # Include formats that have a known resolution or are purely audio with known codec
        if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
            quality = "Audio" if f.get('vcodec') == 'none' else f"{f.get('height', '?')}p"
            ext = f.get('ext', 'unknown')

            size = f.get('filesize') or f.get('filesize_approx')
            size_str = format_size(size)

            valid_formats.append({
                'format_id': f.get('format_id'),
                'quality': quality,
                'ext': ext,
                'size_str': size_str,
                'size_bytes': size
            })

    # Deduplicate slightly by keeping best option per quality+ext combination (naive approach)
    # To keep it simple and robust, let's just return a subset.
    # User can select. Let's return max 15 buttons.
    return valid_formats[-15:] # usually best formats are at the end

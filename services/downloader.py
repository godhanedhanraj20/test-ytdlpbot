import os
import re
import shutil
import uuid
import asyncio
import time
from yt_dlp import YoutubeDL
from typing import Dict, Any, List

from core.limits import is_cancel_requested
from core.logger import setup_logger

logger = setup_logger(__name__, "YT-DLP")

DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class CancelledError(Exception):
    pass

def _extract_info_sync(url: str) -> Dict[str, Any]:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept-Language': 'en-US,en;q=0.9',
        },

        'geo_bypass': True,
        'source_address': '0.0.0.0',
        'retries': 3,
        'fragment_retries': 3,
    }
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

async def extract_video_info(url: str) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(asyncio.to_thread(_extract_info_sync, url), timeout=60)
    except asyncio.TimeoutError:
        logger.warning(f"Timeout extracting info for {url}")
        raise ValueError("Extraction timed out. The video might be too large or unavailable.")
    except Exception as e:
        error_str = str(e).lower()
        logger.error(f"Failed to extract info for {url}: {e}")

        if "sign in" in error_str or "login" in error_str or "bot" in error_str:
            raise ValueError("Video is restricted or blocked by YouTube anti-bot checks.\n\n**How to bypass:**\n1. Try a different video link.\n2. Deploy this bot on a residential IP or VPS (Google Cloud IPs are often blocked).\n3. (Advanced) Configure yt-dlp with `--cookies` in the source code.")
        elif "private" in error_str:
            raise ValueError("This video is private.")
        else:
            raise ValueError("Failed to extract video information. It might be restricted or unsupported.")




class ExtractionError(Exception):
    pass

class NetworkError(Exception):
    pass

class AuthError(Exception):
    pass

def _download_video_sync(url: str, format_id: str, user_id: int, loop: asyncio.AbstractEventLoop, progress_callback=None) -> str:
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f'%(title)s_{unique_id}.%(ext)s')

    # We will try the requested format+bestaudio/best first, then fallback to 'best'
    formats_to_try = [
        f'{format_id}+bestaudio/best',
        'best'
    ]

    last_error = None

    for fmt in formats_to_try:
        ydl_opts = {
            'format': fmt,
            'merge_output_format': 'mp4',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            },
            'geo_bypass': True,
            'source_address': '0.0.0.0',
            'retries': 3,
            'fragment_retries': 3,
        }

        milestones_reached = set()

        if progress_callback:
            def hook(d):
                future = asyncio.run_coroutine_threadsafe(is_cancel_requested(user_id), loop)
                try:
                    cancel_requested = future.result(timeout=2)
                    if cancel_requested:
                        raise CancelledError("User requested cancellation.")
                except CancelledError:
                    raise
                except Exception:
                    pass

                if d['status'] == 'downloading':
                    percent_str = d.get('_percent_str', '0%').replace('%', '').strip()
                    try:
                        percent_val = float(percent_str)

                        # Log milestones
                        for milestone in [10, 25, 50, 75, 100]:
                            if percent_val >= milestone and milestone not in milestones_reached:
                                logger.info(f"User {user_id} download progress: {milestone}%")
                                milestones_reached.add(milestone)

                    except ValueError:
                        pass

                    speed = d.get('_speed_str', 'N/A')
                if isinstance(speed, str):
                    speed = re.sub(r'\x1B(?:[@-Z\\-_]|\\[[0-?]*[ -/]*[@-~])', '', speed).strip()
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    eta = d.get('eta', 0)

                    progress_callback(d.get('_percent_str', '0%'), speed, downloaded, total, eta)

            ydl_opts['progress_hooks'] = [hook]

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

                # Handling merged formats
                if not os.path.exists(filename):
                     for file in os.listdir(DOWNLOAD_DIR):
                         if unique_id in file:
                             return os.path.join(DOWNLOAD_DIR, file)

                return filename

        except CancelledError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "user requested cancellation" in error_str:
                raise CancelledError("User requested cancellation.")

            # Categorize the error
            if "sign in" in error_str or "login" in error_str or "403" in error_str or "forbidden" in error_str:
                last_error = AuthError("Video requires login or is age-restricted")
            elif "extract" in error_str:
                last_error = ExtractionError(f"Extraction failed: {e}")
            elif "network" in error_str or "connection" in error_str:
                last_error = NetworkError(f"Network error: {e}")
            else:
                last_error = Exception(f"yt-dlp error: {e}")

            logger.warning(f"Download failed for format {fmt} with error: {str(last_error)}. Retrying with fallback if available.")
            continue # Try next format in list

    # If we exhaust all formats, raise the last error
    if last_error:
        raise last_error

    raise Exception("Failed to download video with all available formats.")

async def download_video(url: str, format_id: str, user_id: int, progress_message_func=None) -> str:
    # Ensure system supports merging
    if not shutil.which("ffmpeg"):
        logger.warning("FFmpeg not found. High-quality formats may fail to merge.")

    last_update_time = [time.time()]
    loop = asyncio.get_running_loop()

    def sync_progress_callback(percent: str, speed: str, downloaded: int, total: int, eta: int):
        if not progress_message_func:
            return

        current_time = time.time()
        if current_time - last_update_time[0] > 3:
            last_update_time[0] = current_time
            progress_message_func(percent, speed, downloaded, total, eta)

    try:
        logger.info(f"Starting download for user {user_id} with format {format_id}")
        file_path = await asyncio.wait_for(
            asyncio.to_thread(_download_video_sync, url, format_id, user_id, loop, sync_progress_callback),
            timeout=600 # STRICT 10 MINUTE TIMEOUT
        )
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("Downloaded file could not be found.")
        logger.info(f"Download completed for user {user_id}: {file_path}")
        return file_path
    except CancelledError:
        logger.info(f"Download cancelled by user {user_id}")
        raise
    except asyncio.TimeoutError:
        logger.warning(f"Download timed out after 10 mins for user {user_id}")
        raise Exception("Download timed out (10 minutes).")
    except AuthError as e:
        logger.error(f"Auth error for user {user_id}: {e}")
        raise AuthError(str(e))
    except ExtractionError as e:
        logger.error(f"Extraction error for user {user_id}: {e}")
        raise ExtractionError(str(e))
    except NetworkError as e:
        logger.error(f"Network error for user {user_id}: {e}")
        raise NetworkError(str(e))
    except Exception as e:
        if "User requested cancellation" in str(e):
            logger.info(f"Download cancelled by user {user_id}")
            raise CancelledError("User requested cancellation.")
        logger.error(f"Download failed for user {user_id}: {e}")
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
    video_formats = []
    audio_formats = []

    for f in formats:
        size = f.get('filesize') or f.get('filesize_approx') or 0
        ext = f.get('ext', 'unknown')
        format_id = f.get('format_id')

        is_video = f.get('vcodec') != 'none'
        is_audio = f.get('acodec') != 'none'

        if not is_video and not is_audio:
            continue

        item = {
            'format_id': format_id,
            'ext': ext,
            'size_str': format_size(size),
            'size_bytes': size,
            'height': f.get('height', 0)
        }

        if is_video:
            item['type'] = 'video'
            item['quality'] = f"{f.get('height', '?')}p"
            item['is_video_only'] = not is_audio
            video_formats.append(item)
        elif is_audio:
            item['type'] = 'audio'
            item['quality'] = "Audio"
            item['is_video_only'] = False
            audio_formats.append(item)

    # STRICT SORTING
    # Video: Resolution High -> Low
    video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
    # Audio: Size Small -> Large
    audio_formats.sort(key=lambda x: x.get('size_bytes', 0))

    clean_video = []
    seen_res = set()
    for v in video_formats:
        if v['quality'] not in seen_res:
            seen_res.add(v['quality'])
            clean_video.append(v)
            if len(clean_video) >= 10:
                break

    valid_formats = clean_video + audio_formats[:4]
    return valid_formats

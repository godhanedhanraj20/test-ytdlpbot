import os
import uuid
import asyncio
import time
from yt_dlp import YoutubeDL
from typing import Dict, Any, List

from core.limits import is_cancel_requested

DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class CancelledError(Exception):
    pass

def _extract_info_sync(url: str) -> Dict[str, Any]:
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    with YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

async def extract_video_info(url: str) -> Dict[str, Any]:
    try:
        return await asyncio.wait_for(asyncio.to_thread(_extract_info_sync, url), timeout=60)
    except asyncio.TimeoutError:
        raise ValueError("Timeout extracting video information.")
    except Exception as e:
        raise ValueError(f"Failed to extract info: {str(e)}")

def _download_video_sync(url: str, format_id: str, user_id: int, loop: asyncio.AbstractEventLoop, progress_callback=None) -> str:
    unique_id = str(uuid.uuid4())
    output_template = os.path.join(DOWNLOAD_DIR, f'%(title)s_{unique_id}.%(ext)s')

    ydl_opts = {
        'format': format_id,
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,
    }

    if progress_callback:
        def hook(d):
            # Check cancel state securely from async context
            # By passing task safely
            future = asyncio.run_coroutine_threadsafe(is_cancel_requested(user_id), loop)
            try:
                # blocks thread slightly, but ok for yt-dlp hook
                cancel_requested = future.result(timeout=2)
                if cancel_requested:
                    raise CancelledError("User requested cancellation.")
            except CancelledError:
                raise
            except Exception:
                pass

            if d['status'] == 'downloading':
                percent = d.get('_percent_str', '0%')
                speed = d.get('_speed_str', 'N/A')
                progress_callback(percent, speed)
        ydl_opts['progress_hooks'] = [hook]

    with YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                 for file in os.listdir(DOWNLOAD_DIR):
                     if unique_id in file:
                         return os.path.join(DOWNLOAD_DIR, file)

            return filename
        except CancelledError:
            raise
        except Exception as e:
            if "User requested cancellation" in str(e):
                raise CancelledError("User requested cancellation.")
            raise e

async def download_video(url: str, format_id: str, user_id: int, progress_message_func=None) -> str:
    last_update_time = [time.time()]
    loop = asyncio.get_running_loop()

    def sync_progress_callback(percent: str, speed: str):
        if not progress_message_func:
            return

        current_time = time.time()
        # Update every 3 seconds
        if current_time - last_update_time[0] > 3:
            last_update_time[0] = current_time
            asyncio.run_coroutine_threadsafe(
                progress_message_func(percent, speed),
                loop
            )

    try:
        file_path = await asyncio.wait_for(
            asyncio.to_thread(_download_video_sync, url, format_id, user_id, loop, sync_progress_callback),
            timeout=900
        )
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError("Downloaded file could not be found.")
        return file_path
    except CancelledError:
        raise
    except asyncio.TimeoutError:
        raise Exception("Download timed out (15 minutes).")
    except Exception as e:
        if "User requested cancellation" in str(e):
            raise CancelledError("User requested cancellation.")
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
            video_formats.append(item)
        elif is_audio:
            item['type'] = 'audio'
            item['quality'] = "Audio"
            audio_formats.append(item)

    video_formats.sort(key=lambda x: (x.get('height', 0), x.get('size_bytes', 0)), reverse=True)
    audio_formats.sort(key=lambda x: x.get('size_bytes', 0), reverse=True)

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

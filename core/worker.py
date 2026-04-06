import asyncio
import logging
import os
from arq.connections import RedisSettings
from services.downloader import download_video, CancelledError
from core.queue import REDIS_URL
from core.cache import set_progress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

async def download_task(ctx, url: str, format_id: str, user_id: int):
    """
    ARQ Background Task to download the video using yt-dlp.
    It writes progress to Redis so the Bot process can read it.
    """
    job_id = ctx['job_id']
    logger.info(f"Worker started job {job_id} for user {user_id}")

    # Synchronous progress hook adapted for Redis storage via async queue
    def progress_callback(percent: str, speed: str):
        # We must fire and forget the async redis write from sync context
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                set_progress(job_id, percent, speed),
                loop
            )
        except Exception as e:
            logger.error(f"Failed to set progress: {e}")

    try:
        file_path = await download_video(url, format_id, user_id, progress_message_func=progress_callback)
        logger.info(f"Worker completed job {job_id}. File: {file_path}")
        return {"status": "success", "file_path": file_path}
    except CancelledError:
        logger.info(f"Worker cancelled job {job_id} for user {user_id}")
        return {"status": "cancelled"}
    except Exception as e:
        logger.error(f"Worker failed job {job_id}: {e}", exc_info=True)
        return {"status": "error", "error_message": str(e)}

# Parse REDIS_URL for ARQ worker settings
host = "localhost"
port = 6379
database = 0
password = None

if REDIS_URL.startswith("redis://"):
    try:
        url_part = REDIS_URL.replace("redis://", "")
        auth_part, host_part = "", url_part
        if "@" in url_part:
            auth_part, host_part = url_part.split("@", 1)
            if ":" in auth_part:
                _, password = auth_part.split(":", 1)
            else:
                password = auth_part

        if "/" in host_part:
            host_port, db_part = host_part.split("/", 1)
            database = int(db_part)
        else:
            host_port = host_part

        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            port = int(port_str)
        else:
            host = host_port
    except Exception:
        pass

# Settings class for ARQ CLI
class WorkerSettings:
    functions = [download_task]
    redis_settings = RedisSettings(host=host, port=port, database=database, password=password)
    max_jobs = 2

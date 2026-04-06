import asyncio
import os
from arq.connections import RedisSettings
from services.downloader import download_video, CancelledError
from core.queue import REDIS_URL
from core.cache import set_progress, set_job_status
from core.logger import setup_logger

logger = setup_logger("worker", "WORKER")

async def download_task(ctx, url: str, format_id: str, user_id: int):
    """
    ARQ Background Task to download the video using yt-dlp.
    Includes retry logic, structured error handling, and Redis job status tracking.
    """
    job_id = ctx['job_id']
    logger.info(f"Worker started job {job_id} for user {user_id}")
    await set_job_status(job_id, user_id, "downloading")

    def progress_callback(percent: str, speed: str):
        try:
            loop = asyncio.get_running_loop()
            asyncio.run_coroutine_threadsafe(
                set_progress(job_id, percent, speed),
                loop
            )
        except Exception as e:
            logger.error(f"Failed to set progress for job {job_id}: {e}")

    max_retries = 2
    retry_delay = 3

    for attempt in range(max_retries + 1):
        try:
            file_path = await download_video(url, format_id, user_id, progress_message_func=progress_callback)
            logger.info(f"Worker successfully completed job {job_id}. File: {file_path}")
            await set_job_status(job_id, user_id, "completed")
            return {"status": "success", "file_path": file_path}

        except CancelledError:
            logger.info(f"Worker cancelled job {job_id} for user {user_id}")
            await set_job_status(job_id, user_id, "failed")
            return {"status": "cancelled", "error_type": "CancelledError", "message": "Task cancelled by user."}

        except Exception as e:
            error_str = str(e)
            logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed for job {job_id}: {error_str}")

            # Check if it's a retryable network or temporary yt-dlp error
            # Simple heuristic: if 'HTTP' or 'timed out' or 'network' in error string
            is_retryable = any(kw in error_str.lower() for kw in ['http', 'time', 'network', 'connection', 'unavailable'])

            if attempt < max_retries and is_retryable:
                logger.info(f"Retrying job {job_id} in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                continue

            logger.error(f"Worker failed job {job_id} permanently: {error_str}", exc_info=True)
            await set_job_status(job_id, user_id, "failed")
            return {
                "status": "error",
                "error_type": "DownloadError",
                "message": f"Failed to download video: {error_str}"
            }

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

class WorkerSettings:
    functions = [download_task]
    redis_settings = RedisSettings(host=host, port=port, database=database, password=password)
    max_jobs = 2

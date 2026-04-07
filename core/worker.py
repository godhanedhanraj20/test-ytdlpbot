import os
from dotenv import load_dotenv
load_dotenv("config.env")

import asyncio
import os
from arq.connections import RedisSettings
from services.downloader import download_video, CancelledError, AuthError, ExtractionError, NetworkError
from core.queue import REDIS_URL
from core.cache import set_progress, set_job_status, add_active_job, remove_active_job
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
    await add_active_job(job_id)

    def progress_callback(percent: str, speed: str, downloaded: int, total: int, eta: int):
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                set_progress(job_id, percent, speed, downloaded, total, eta),
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
            await remove_active_job(job_id)
            return {"status": "success", "file_path": file_path}


        except CancelledError:
            logger.info(f"Worker cancelled job {job_id} for user {user_id}")
            await set_job_status(job_id, user_id, "failed")
            await remove_active_job(job_id)
            return {"status": "cancelled", "error_type": "CancelledError", "message": "Task cancelled by user."}

        except AuthError as e:
            logger.error(f"Worker failed job {job_id} permanently due to Auth Error: {e}")
            await set_job_status(job_id, user_id, "failed")
            await remove_active_job(job_id)
            return {
                "status": "error",
                "error_type": "AuthError",
                "message": "Video requires login or is age-restricted and cannot be downloaded without cookies."
            }

        except ExtractionError as e:
            logger.error(f"Worker failed job {job_id} permanently due to Extraction Error: {e}")
            await set_job_status(job_id, user_id, "failed")
            await remove_active_job(job_id)
            return {
                "status": "error",
                "error_type": "ExtractionError",
                "message": "Video cannot be accessed or extracted."
            }

        except Exception as e:
            error_str = str(e)
            logger.warning(f"Attempt {attempt + 1}/{max_retries + 1} failed for job {job_id}: {error_str}")

            is_retryable = any(kw in error_str.lower() for kw in ['http', 'time', 'network', 'connection', 'unavailable', 'reset']) or isinstance(e, NetworkError)

            if attempt < max_retries and is_retryable:
                logger.info(f"Retrying job {job_id} in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                continue

            logger.error(f"Worker failed job {job_id} permanently: {error_str}")
            await set_job_status(job_id, user_id, "failed")
            await remove_active_job(job_id)
            return {
                "status": "error",
                "error_type": "DownloadError",
                "message": f"Video may be restricted or temporarily unavailable. Details: {error_str[:100]}"
            }

class WorkerSettings:
    functions = [download_task]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = 2

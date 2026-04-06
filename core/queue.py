import asyncio
import logging
from typing import Callable, Coroutine

logger = logging.getLogger(__name__)

# Queue to hold download tasks
download_queue = asyncio.Queue()

async def worker(app):
    """
    Background worker that processes items from the download_queue sequentially.
    """
    logger.info("Download queue worker started.")
    while True:
        task = await download_queue.get()
        try:
            # task is expected to be a coroutine function
            await task()
        except Exception as e:
            logger.error(f"Worker caught exception: {e}", exc_info=True)
        finally:
            download_queue.task_done()

def start_workers(app, num_workers=2):
    """
    Start the background workers.
    """
    for _ in range(num_workers):
        asyncio.create_task(worker(app))

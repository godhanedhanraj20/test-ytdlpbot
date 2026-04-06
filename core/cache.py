import time
import uuid
import json
from core.redis import redis_client

CACHE_TTL = 300  # 5 minutes
STATUS_TTL = 3600 # 1 hour

def generate_short_id() -> str:
    return uuid.uuid4().hex[:8]

async def store_format_data(url: str, format_id: str, size_bytes: int, title: str = 'Unknown Title') -> str:
    short_id = generate_short_id()
    data = {
        "url": url,
        "format_id": format_id,
        "size_bytes": size_bytes,
        "title": title,
        "timestamp": time.time()
    }
    await redis_client.setex(f"format:{short_id}", CACHE_TTL, json.dumps(data))
    return short_id

async def get_format_data(short_id: str) -> dict:
    raw_data = await redis_client.get(f"format:{short_id}")
    if raw_data:
        return json.loads(raw_data)
    return None

async def set_progress(job_id: str, percent: str, speed: str, downloaded: int = 0, total: int = 0, eta: int = 0):
    data = {"percent": percent, "speed": speed, "downloaded": downloaded, "total": total, "eta": eta, "timestamp": time.time()}
    await redis_client.setex(f"progress:{job_id}", STATUS_TTL, json.dumps(data))

async def get_progress(job_id: str) -> dict:
    raw_data = await redis_client.get(f"progress:{job_id}")
    if raw_data:
        return json.loads(raw_data)
    return None

async def set_job_status(job_id: str, user_id: int, status: str):
    """
    Status tracking: queued, downloading, uploading, completed, failed
    """
    data = {
        "job_id": job_id,
        "user_id": user_id,
        "status": status,
        "timestamp": time.time()
    }
    await redis_client.setex(f"status:{job_id}", STATUS_TTL, json.dumps(data))

async def get_job_status(job_id: str) -> dict:
    raw_data = await redis_client.get(f"status:{job_id}")
    if raw_data:
        return json.loads(raw_data)
    return None

async def cleanup_job_data(job_id: str):
    """Cleans up temporary tracking keys once a job finishes."""
    await redis_client.delete(f"progress:{job_id}")
    await redis_client.delete(f"status:{job_id}")

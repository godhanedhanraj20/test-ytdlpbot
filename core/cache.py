import time
import uuid
import json
from core.redis import redis_client

CACHE_TTL = 300  # 5 minutes

def generate_short_id() -> str:
    return uuid.uuid4().hex[:8]

async def store_format_data(url: str, format_id: str, size_bytes: int) -> str:
    short_id = generate_short_id()
    data = {
        "url": url,
        "format_id": format_id,
        "size_bytes": size_bytes,
        "timestamp": time.time()
    }
    await redis_client.setex(f"format:{short_id}", CACHE_TTL, json.dumps(data))
    return short_id

async def get_format_data(short_id: str) -> dict:
    raw_data = await redis_client.get(f"format:{short_id}")
    if raw_data:
        return json.loads(raw_data)
    return None

async def set_progress(job_id: str, percent: str, speed: str):
    data = {"percent": percent, "speed": speed, "timestamp": time.time()}
    await redis_client.setex(f"progress:{job_id}", 3600, json.dumps(data))

async def get_progress(job_id: str) -> dict:
    raw_data = await redis_client.get(f"progress:{job_id}")
    if raw_data:
        return json.loads(raw_data)
    return None

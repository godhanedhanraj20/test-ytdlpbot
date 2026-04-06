import time
import uuid

# In-memory storage: { short_id: {"url": str, "format_id": str, "size_bytes": int, "timestamp": float} }
_cache = {}

CACHE_TTL = 300  # 5 minutes

def generate_short_id() -> str:
    return uuid.uuid4().hex[:8]

def store_format_data(url: str, format_id: str, size_bytes: int) -> str:
    cleanup_cache()
    short_id = generate_short_id()
    _cache[short_id] = {
        "url": url,
        "format_id": format_id,
        "size_bytes": size_bytes,
        "timestamp": time.time()
    }
    return short_id

def get_format_data(short_id: str) -> dict:
    cleanup_cache()
    data = _cache.get(short_id)
    if data:
        # Optionally remove after use, but let's keep it until TTL expires
        # so if the user clicks again we can show "Already processing" instead of "Expired".
        return data
    return None

def cleanup_cache():
    now = time.time()
    expired = [k for k, v in _cache.items() if now - v["timestamp"] > CACHE_TTL]
    for k in expired:
        del _cache[k]

import json
from core.redis import redis_client

DEFAULT_SETTINGS = {
  "mode": "video",
  "send_as": "media",
  "quality": "ask",
  "prefix": "",
  "suffix": "",
  "thumbnail": None,
  "auto_best": False
}

async def init_user_settings(user_id: int):
    """Initializes user settings if they don't exist."""
    key = f"user_settings:{user_id}"
    if not await redis_client.exists(key):
        await redis_client.set(key, json.dumps(DEFAULT_SETTINGS))

async def get_user_settings(user_id: int) -> dict:
    """Retrieves user settings from Redis, filling missing keys with defaults."""
    key = f"user_settings:{user_id}"
    raw = await redis_client.get(key)

    settings = DEFAULT_SETTINGS.copy()
    if raw:
        try:
            stored = json.loads(raw)
            settings.update(stored)
        except json.JSONDecodeError:
            pass
    return settings

async def update_user_settings(user_id: int, new_data: dict):
    """Updates user settings in Redis."""
    settings = await get_user_settings(user_id)
    settings.update(new_data)

    # Safe trimming
    if "prefix" in settings and settings["prefix"]:
        settings["prefix"] = settings["prefix"][:30]
    if "suffix" in settings and settings["suffix"]:
        settings["suffix"] = settings["suffix"][:30]

    await redis_client.set(f"user_settings:{user_id}", json.dumps(settings))

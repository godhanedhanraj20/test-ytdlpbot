from core.redis import redis_client

async def acquire_lock(user_id: int) -> bool:
    success = await redis_client.setnx(f"lock:{user_id}", "1")
    if success:
        await redis_client.expire(f"lock:{user_id}", 3600)
        return True
    return False

async def release_lock(user_id: int):
    await redis_client.delete(f"lock:{user_id}")
    await redis_client.delete(f"cancel:{user_id}")

async def request_cancel(user_id: int) -> bool:
    is_locked = await redis_client.exists(f"lock:{user_id}")
    if is_locked:
        await redis_client.setex(f"cancel:{user_id}", 3600, "1")
        return True
    return False

async def is_cancel_requested(user_id: int) -> bool:
    return await redis_client.exists(f"cancel:{user_id}")

async def check_rate_limit(user_id: int) -> bool:
    """
    Max 5 downloads per user per 15 minutes.
    Returns True if allowed, False if exceeded.
    """
    key = f"rate_limit:{user_id}"

    # Increment the counter
    count = await redis_client.incr(key)

    if count == 1:
        # First request in the window, set expiry for 15 minutes (900 seconds)
        await redis_client.expire(key, 900)

    if count > 5:
        return False

    return True


async def is_locked(user_id: int) -> bool:
    return await redis_client.exists(f"lock:{user_id}")

from core.redis import redis_client

async def acquire_lock(user_id: int) -> bool:
    # Setnx returns True if key was set (user wasn't active), False otherwise
    success = await redis_client.setnx(f"lock:{user_id}", "1")
    if success:
        # Prevent absolute deadlock if bot crashes, expire lock after 1 hour
        await redis_client.expire(f"lock:{user_id}", 3600)
        return True
    return False

async def release_lock(user_id: int):
    await redis_client.delete(f"lock:{user_id}")
    await redis_client.delete(f"cancel:{user_id}")

async def request_cancel(user_id: int) -> bool:
    # Only allow cancel if user is currently locked
    is_locked = await redis_client.exists(f"lock:{user_id}")
    if is_locked:
        await redis_client.setex(f"cancel:{user_id}", 3600, "1")
        return True
    return False

async def is_cancel_requested(user_id: int) -> bool:
    return await redis_client.exists(f"cancel:{user_id}")

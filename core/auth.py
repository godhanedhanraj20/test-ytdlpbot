import os
import logging
from core.redis import redis_client

logger = logging.getLogger(__name__)

# The main admin user who can add others
ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID")
if ADMIN_USER_ID:
    try:
        ADMIN_USER_ID = int(ADMIN_USER_ID)
    except ValueError:
        logger.error("ADMIN_USER_ID environment variable must be an integer.")
        ADMIN_USER_ID = None

async def is_user_allowed(user_id: int) -> bool:
    """
    Checks if a user is allowed to use the bot.
    The ADMIN_USER_ID is always allowed.
    """
    if ADMIN_USER_ID and user_id == ADMIN_USER_ID:
        return True

    # Check persistent whitelist in Redis
    return await redis_client.sismember("allowed_users", str(user_id))

async def add_allowed_user(user_id: int) -> bool:
    """
    Adds a user to the Redis persistent whitelist.
    """
    return await redis_client.sadd("allowed_users", str(user_id)) > 0

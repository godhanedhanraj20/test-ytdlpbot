import os
from dotenv import load_dotenv
load_dotenv("config.env")

import os
from arq import create_pool
from arq.connections import RedisSettings

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

async def get_arq_pool():
    # Use ARQ's built in DSN parser which natively supports redis:// and rediss://
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    return await create_pool(redis_settings)

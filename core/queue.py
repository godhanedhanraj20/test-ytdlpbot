import os
from arq import create_pool
from arq.connections import RedisSettings

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

async def get_arq_pool():
    # ARQ uses its own RedisSettings format
    # We parse standard redis:// url (naive parsing for simplicity)
    # redis://[password@]host:port/database
    host = "localhost"
    port = 6379
    database = 0
    password = None

    if REDIS_URL.startswith("redis://"):
        try:
            url_part = REDIS_URL.replace("redis://", "")
            auth_part, host_part = "", url_part
            if "@" in url_part:
                auth_part, host_part = url_part.split("@", 1)
                if ":" in auth_part:
                    _, password = auth_part.split(":", 1)
                else:
                    password = auth_part

            if "/" in host_part:
                host_port, db_part = host_part.split("/", 1)
                database = int(db_part)
            else:
                host_port = host_part

            if ":" in host_port:
                host, port_str = host_port.split(":", 1)
                port = int(port_str)
            else:
                host = host_port
        except Exception:
            pass # fallback to localhost:6379/0 if parsing fails

    redis_settings = RedisSettings(host=host, port=port, database=database, password=password)
    return await create_pool(redis_settings)

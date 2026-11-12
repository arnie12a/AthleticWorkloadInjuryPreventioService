import os
import redis
from dotenv import load_dotenv
from redis.exceptions import RedisError

def invalidate_workload_cache(user_id):
    cache_key = f"workload:trends:{user_id}"

    try:
        redis_client.delete(cache_key)
    except RedisError:
        pass

load_dotenv()

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6379/0"
)

redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=10,
    health_check_interval=30
)


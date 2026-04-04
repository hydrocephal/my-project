import redis.asyncio as aioredis

from app.core.config import settings

redis_client: aioredis.Redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

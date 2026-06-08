import redis.asyncio as redis
import logging
from typing import Optional
from cache_settings.config import settings

logger = logging.getLogger(__name__)

class RedisClientManager:
    """Singleton менеджер для Redis соединения"""
    _instance: Optional['RedisClientManager'] = None
    _client: Optional[redis.Redis] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    async def connect(self, redis_url: str = None):
        """Установка соединения с Redis"""
        if self._client is None:
            redis_url = redis_url or settings.REDIS_URL
            self._client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            try:
                await self._client.ping()
                logger.info(f"Connected to Redis at {redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._client = None
                raise
        return self._client
    
    async def disconnect(self):
        """Закрытие соединения с Redis"""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")
    
    def get_client(self) -> Optional[redis.Redis]:
        """Получение клиента Redis"""
        return self._client

redis_manager = RedisClientManager()

async def get_redis() -> redis.Redis:
    client = redis_manager.get_client()
    if client is None:
        raise RuntimeError("Redis not connected")
    return client

async def init_redis(redis_url: str = None):
    return await redis_manager.connect(redis_url)

async def close_redis():
    await redis_manager.disconnect()
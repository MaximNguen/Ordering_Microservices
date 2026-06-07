import json
import logging
from typing import Any, Optional, Callable, Awaitable
import redis.asyncio as redis
from cache_settings.redis_client import get_redis
from datetime import datetime

logger = logging.getLogger(__name__)

class CacheManager:
    """Менеджер кеша с поддержкой инвалидации по событиям (Создание заказа -> Инвалидация кеша и тд)"""
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self._subscribers: dict[str, list[Callable[[dict], Awaitable[None]]]] = {}
    
    def _make_key(self, key: str) -> str:
        return f"{self.prefix}:{key}" if self.prefix else key
    
    async def get(self, key: str) -> Optional[Any]:
        """Получение значения из кеша"""
        
        try: 
            redis_client = await get_redis()
            data = await redis_client.get(self._make_key(key))
            if data is not None:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {e}")
            return None
        
    async def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Установка значения в кеш с опциональным временем жизни"""
        try:
            redis_client = await get_redis()
            await redis_client.setex(self._make_key(key), expire, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {e}")
            return False
        
    async def delete(self, key: str) -> bool:
        """Удаление значения из кеша"""
        try:
            redis_client = await get_redis()
            await redis_client.delete(self._make_key(key))
            logger.info(f"Cache deleted for key {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {e}")
            return False
        
    async def delete_pattern(self, pattern: str) -> bool:
        """Удалить все ключи по паттерну"""
        
        try:
            redis_client = await get_redis()
            keys = await redis_client.keys(self._make_key(pattern))
            if keys:
                await redis_client.delete(*keys)
                logger.info(f"Cache deleted for pattern {pattern} (keys: {keys})")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache for pattern {pattern}: {e}")
            return False
    
    async def publish_event(self, event_type: str, data: dict):
        """Публикация события для инвалидации кеша"""
        try:
            redis_client = await get_redis()
            event = {
                "event_type": event_type,
                "data": data,
                "service": self.prefix,
                "timestamp": datetime.now().isoformat()
            }
            await redis_client.publish(
                "cache:invalidation",
                json.dumps(event, default=str)
            )
            logger.info(f"Published cache event {event} with data {data}")
        except Exception as e:
            logger.error(f"Error publishing cache event: {e}")
            
    async def subscribe_to_events(self, callback: Callable[[dict], Awaitable[None]]):
        """Подписаться на события инвалидации кеша"""
        try:
            redis_client = await get_redis()
            pubsub = redis_client.pubsub()
            await pubsub.subscribe("cache:invalidation")
            
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        event = json.loads(message['data'])
                        if event.get('service') != self.prefix:
                            await callback(event)
                    except Exception as e:
                        logger.error(f"Error processing invalidation event: {e}")
        except Exception as e:
            logger.error(f"Error subscribing to events: {e}")
            
order_cache = CacheManager(prefix="order")
delivery_cache = CacheManager(prefix="delivery")
product_cache = CacheManager(prefix="product")

class OrderCacheKeys:
    ORDER_BY_ID = "order:{order_id}"
    ALL_ORDERS = "all_orders:skip:{skip}:limit:{limit}"
    ALL_ORDERS_FILTERED = "all_orders:skip:{skip}:limit:{limit}:user:{user_id}:status:{status}"
    USER_ORDERS = "user:{user_id}:orders"
    
class DeliveryCacheKeys:
    DELIVERY_BY_ID = "delivery:{delivery_id}"
    ALL_DELIVERIES = "all_deliveries:skip:{skip}:limit:{limit}"
    
class ProductCacheKeys:
    PRODUCT_BY_ID = "product:{product_id}"
    ALL_PRODUCTS = "all_products:skip:{skip}:limit:{limit}"
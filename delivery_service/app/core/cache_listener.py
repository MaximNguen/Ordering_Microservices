import asyncio
import logging
from typing import Optional
from cache_settings.cache_manager import delivery_cache, DeliveryCacheKeys
from cache_settings.redis_client import get_redis

logger = logging.getLogger(__name__)

class CacheInvalidationListener:
    """Слушает события инвалидации кеша для сервиса доставок"""
    
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
    
    async def handle_invalidation_event(self, event: dict):
        """Обработчик событий инвалидации"""
        event_type = event.get('event_type')
        data = event.get('data', {})
        service = event.get('service')
        
        logger.info(f"Received invalidation event: {event_type} from {service}")
        
        if event_type == "order.updated" or event_type == "order.status_changed":
            order_id = data.get('order_id')
            if order_id:
                await delivery_cache.delete_pattern(f"*order_id:{order_id}*")
                logger.info(f"Invalidated delivery caches for order: {order_id}")

        elif event_type == "product.updated":
            await delivery_cache.delete_pattern("delivery:*")
            logger.info(f"Invalidated all delivery caches due to product update: {data.get('product_id')}")
            
        elif event_type == "product.deleted":
            await delivery_cache.delete_pattern("delivery:*")
            logger.info(f"Invalidated all delivery caches due to product deletion: {data.get('product_id')}")
        
        elif event_type == "delivery.updated":
            delivery_id = data.get('delivery_id')
            if delivery_id:
                await delivery_cache.delete(DeliveryCacheKeys.DELIVERY_BY_ID.format(delivery_id=delivery_id))
                logger.info(f"Invalidated delivery cache for delivery: {delivery_id}")
    
    async def start_listening(self):
        """Запуск слушателя событий"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                logger.info("Starting delivery cache invalidation listener...")
                redis_client = await get_redis()
                await redis_client.ping()
                await delivery_cache.subscribe_to_events(self.handle_invalidation_event)
                return
            except Exception as e:
                logger.error(f"Failed to start listener (attempt {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    raise
    
    def start(self):
        """Запуск в фоновом режиме"""
        self._task = asyncio.create_task(self.start_listening())
        logger.info("Delivery cache invalidation listener started")
    
    async def stop(self):
        """Остановка слушателя"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Delivery cache invalidation listener stopped")
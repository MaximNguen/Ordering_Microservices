import asyncio
import logging
from typing import Optional
from shared.cache_manager import order_cache, OrderCacheKeys

logger = logging.getLogger(__name__)

class CacheInvalidationListener:
    """Слушает события инвалидации кеша от других сервисов"""
    
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
    
    async def handle_invalidation_event(self, event: dict):
        """Обработчик событий инвалидации"""
        event_type = event.get('event_type')
        data = event.get('data', {})
        service = event.get('service')
        
        logger.info(f"Received invalidation event: {event_type} from {service}")
        
        if event_type == "product.updated":
            await order_cache.delete_pattern("order:*")
            logger.info(f"Invalidated all order caches due to product update: {data.get('product_id')}")
            
        elif event_type == "product.deleted":
            await order_cache.delete_pattern("order:*")
            logger.info(f"Invalidated all order caches due to product deletion: {data.get('product_id')}")
            
        elif event_type == "order.updated":
            order_id = data.get('order_id')
            if order_id:
                await order_cache.delete(OrderCacheKeys.ORDER_BY_ID.format(order_id=order_id))
                logger.info(f"Invalidated order cache for order: {order_id}")
    
    async def start_listening(self):
        """Запуск слушателя событий"""
        logger.info("Starting cache invalidation listener...")
        await order_cache.subscribe_to_events(self.handle_invalidation_event)
    
    def start(self):
        """Запуск в фоновом режиме"""
        self._task = asyncio.create_task(self.start_listening())
        logger.info("Cache invalidation listener started")
    
    async def stop(self):
        """Остановка слушателя"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Cache invalidation listener stopped")
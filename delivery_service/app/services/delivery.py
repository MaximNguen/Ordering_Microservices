import logging
import os
from typing import Optional
import uuid

import httpx

from app.repositories.delivery import DeliveryRepository
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from cache_settings.cache_manager import delivery_cache, DeliveryCacheKeys

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8002").rstrip("/")
INTERNAL_CALL_HEADER = os.getenv("INTERNAL_CALL_HEADER", "X-Internal-Token")
INTERNAL_CALL_TOKEN = os.getenv("INTERNAL_CALL_TOKEN", "")
SKIP_ORDER_CHECK = os.getenv("SKIP_ORDER_CHECK", "false").lower() == "true"

class DeliveryService:
    """Класс-сервис для управления логикой доставки, обеспечивающий взаимодействие между репозиторием и API."""
    def __init__(self, delivery_repo: DeliveryRepository):
        self.delivery_repo = delivery_repo
        self.logger = logging.getLogger(__name__)
        
    async def invalidate_delivery_caches(self, delivery_id: uuid.UUID, order_id: Optional[uuid.UUID] = None):
        """Инвалидация кеша, связанные с доставкой"""
        await delivery_cache.delete(DeliveryCacheKeys.DELIVERY_BY_ID.format(delivery_id=delivery_id))
        
        if order_id:
            await delivery_cache.delete_pattern(f"*order_id:{order_id}*")

        await delivery_cache.delete_pattern("delivery:*")
        
        await delivery_cache.publish_event("delivery.updated", {
            "delivery_id": str(delivery_id),
            "order_id": str(order_id) if order_id else None
        })

    async def create_delivery(self, delivery_create: DeliveryCreate) -> DeliveryResponse | None:
        self.logger.info(f"Создание доставки для заказа {delivery_create.order_id}")
        
        if not SKIP_ORDER_CHECK:
            if not INTERNAL_CALL_TOKEN:
                self.logger.error("INTERNAL_CALL_TOKEN is not configured")
                return None
                
            headers = {INTERNAL_CALL_HEADER: INTERNAL_CALL_TOKEN}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{GATEWAY_URL}/orders/{delivery_create.order_id}",
                    headers=headers,
                )
                
            if response.status_code != 200:
                self.logger.warning(
                    "Заказ не найден или недоступен: %s (status=%s)",
                    delivery_create.order_id,
                    response.status_code,
                )
                return None
        else:
            self.logger.info(f"Пропускаем проверку заказа {delivery_create.order_id} (Kafka режим)")
        
        db_delivery = await self.delivery_repo.create_delivery(
            order_id=delivery_create.order_id,
            address=delivery_create.address,
            delivery_person_id=delivery_create.delivery_person_id,
            scheduled_time=delivery_create.scheduled_time,
            delivery_fee=delivery_create.delivery_fee,
        )
        
        await self.invalidate_delivery_caches(db_delivery.delivery_id, db_delivery.order_id)
        
        return DeliveryResponse.model_validate(db_delivery)
    
    async def get_delivery_by_id(self, delivery_id: uuid.UUID) -> DeliveryResponse | None:
        self.logger.info(f"Получение доставки по ID: {delivery_id}")
        
        cache_key = DeliveryCacheKeys.DELIVERY_BY_ID.format(delivery_id=delivery_id)
        cached_delivery = await delivery_cache.get(cache_key)
        
        if cached_delivery:
            self.logger.info(f"Доставка найдена в кеше: {delivery_id}")
            return DeliveryResponse.model_validate(cached_delivery)
        
        db_delivery = await self.delivery_repo.get_by_delivery_id(delivery_id)
        if not db_delivery:
            return None
        
        delivery_data = DeliveryResponse.model_validate(db_delivery).model_dump()
        
        await delivery_cache.set(cache_key, delivery_data, expire=3600)
        return delivery_data
    
    async def get_all_deliveries(self, skip: int = 0, limit: int = 100) -> list[DeliveryResponse]:
        self.logger.info(f"Получение всех доставок (skip={skip}, limit={limit})")
        
        cache_key = DeliveryCacheKeys.ALL_DELIVERIES.format(skip=skip, limit=limit)
        cached_deliveries = await delivery_cache.get(cache_key)
        
        if cached_deliveries:
            self.logger.info(f"Доставки найдены в кеше (skip={skip}, limit={limit})")
            return [DeliveryResponse.model_validate(delivery) for delivery in cached_deliveries]
        
        db_deliveries = await self.delivery_repo.get_all(skip=skip, limit=limit)
        all_delivery = [DeliveryResponse.model_validate(delivery) for delivery in db_deliveries]
        
        await delivery_cache.set(cache_key, [delivery.model_dump() for delivery in all_delivery], expire=3600)
        return all_delivery
    
    async def update_delivery(self, delivery_id: uuid.UUID, delivery_update: DeliveryUpdate) -> DeliveryResponse | None:
        self.logger.info(f"Обновление доставки с ID: {delivery_id}")
        try:
            db_delivery = await self.delivery_repo.update_delivery(
                delivery_id,
                status=delivery_update.status,
            )
        except ValueError:
            return None
        
        await self.invalidate_delivery_caches(db_delivery.delivery_id, db_delivery.order_id)
        
        await delivery_cache.publish_event("delivery.updated", {
            "delivery_id": str(db_delivery.delivery_id),
            "order_id": str(db_delivery.order_id)
        })

        return DeliveryResponse.model_validate(db_delivery)
    
    async def delete_delivery(self, delivery_id: uuid.UUID) -> bool:
        self.logger.info(f"Удаление доставки с ID: {delivery_id}")
        try:
            await self.delivery_repo.delete_delivery(delivery_id)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при удалении доставки с ID: {delivery_id}, ошибка: {e}")
            return False
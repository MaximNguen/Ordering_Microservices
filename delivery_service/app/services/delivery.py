import logging
import os
from time import time
from typing import Optional
import uuid

import httpx

from app.repositories.delivery import DeliveryRepository
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from cache_settings.cache_manager import delivery_cache, DeliveryCacheKeys
from app.api.main import (
    delivery_created_counter, 
    delivery_updated_counter, 
    delivery_delete_counter, 
    active_deliveries_gauge,
    db_query_duration
)

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
        start_time = time()
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
        
        db_start_time = time()
        db_delivery = await self.delivery_repo.create_delivery(
            order_id=delivery_create.order_id,
            address=delivery_create.address,
            delivery_person_id=delivery_create.delivery_person_id,
            scheduled_time=delivery_create.scheduled_time,
            delivery_fee=delivery_create.delivery_fee,
        )
        
        db_duration = time() - db_start_time
        delivery_created_counter.labels(status="created").inc()
        active_deliveries_gauge.inc()
        
        
        await self.invalidate_delivery_caches(db_delivery.delivery_id, db_delivery.order_id)
        
        total_duration = time() - start_time
        self.logger.info(f"Delivery created in {total_duration:.3f}s (DB: {db_duration:.3f}s)")
        
        return DeliveryResponse.model_validate(db_delivery)
    
    async def get_delivery_by_id(self, delivery_id: uuid.UUID) -> DeliveryResponse | None:
        self.logger.info(f"Получение доставки по ID: {delivery_id}")
        start_time = time()
        cache_start = time()
        
        cache_key = DeliveryCacheKeys.DELIVERY_BY_ID.format(delivery_id=delivery_id)
        cached_delivery = await delivery_cache.get(cache_key)
        cache_duration = time() - cache_start
        
        if cached_delivery:
            self.logger.info(f"Доставка найдена в кеше: {delivery_id} (время: {cache_duration:.3f}s)")
            return DeliveryResponse.model_validate(cached_delivery)
        
        db_start_time = time()
        db_delivery = await self.delivery_repo.get_by_delivery_id(delivery_id)
        db_duration = time() - db_start_time
        
        if not db_delivery:
            return None
        
        db_query_duration.labels(query_type="get_delivery_by_id").observe(db_duration)
        
        delivery_data = DeliveryResponse.model_validate(db_delivery).model_dump()
        
        await delivery_cache.set(cache_key, delivery_data, expire=3600)
        total_duration = time() - start_time
        self.logger.info(f"Delivery retrieved in {total_duration:.3f}s (DB: {db_duration:.3f}s, Cache miss)")
        return delivery_data
    
    async def get_all_deliveries(self, skip: int = 0, limit: int = 100) -> list[DeliveryResponse]:
        self.logger.info(f"Получение всех доставок (skip={skip}, limit={limit})")
        start_time = time()
        
        cache_key = DeliveryCacheKeys.ALL_DELIVERIES.format(skip=skip, limit=limit)
        cached_deliveries = await delivery_cache.get(cache_key)
        
        if cached_deliveries:
            self.logger.info(f"Доставки найдены в кеше (skip={skip}, limit={limit})")
            return [DeliveryResponse.model_validate(delivery) for delivery in cached_deliveries]
        
        db_start_time = time()
        db_deliveries = await self.delivery_repo.get_all(skip=skip, limit=limit)
        db_duration = time() - db_start_time
        
        db_query_duration.labels(query_type="get_all_deliveries").observe(db_duration)
        
        all_delivery = [DeliveryResponse.model_validate(delivery) for delivery in db_deliveries]
        
        await delivery_cache.set(cache_key, [delivery.model_dump() for delivery in all_delivery], expire=3600)
        
        total_duration = time() - start_time
        self.logger.info(f"All deliveries retrieved in {total_duration:.3f}s (DB: {db_duration:.3f}s)")
        
        return all_delivery
    
    async def update_delivery(self, delivery_id: uuid.UUID, delivery_update: DeliveryUpdate) -> DeliveryResponse | None:
        self.logger.info(f"Обновление доставки с ID: {delivery_id}")
        start_time = time()
        
        try:
            db_start_time = time()
            db_delivery = await self.delivery_repo.update_delivery(
                delivery_id,
                status=delivery_update.status,
            )
            db_duration = time() - db_start_time
            db_query_duration.labels(query_type="update_delivery").observe(db_duration)
        except ValueError:
            return None
        
        await self.invalidate_delivery_caches(db_delivery.delivery_id, db_delivery.order_id)
        
        await delivery_cache.publish_event("delivery.updated", {
            "delivery_id": str(db_delivery.delivery_id),
            "order_id": str(db_delivery.order_id)
        })
        total_duration = time() - start_time
        self.logger.info(f"Delivery updated in {total_duration:.3f}s (DB: {db_duration:.3f}s)")

        return DeliveryResponse.model_validate(db_delivery)
    
    async def delete_delivery(self, delivery_id: uuid.UUID) -> bool:
        self.logger.info(f"Удаление доставки с ID: {delivery_id}")
        start_time = time()
        db_delivery = await self.delivery_repo.get_by_delivery_id(delivery_id)
        
        try:
            db_start_time = time()
            await self.delivery_repo.delete_delivery(delivery_id)
            db_duration = time() - db_start_time
            db_query_duration.labels(query_type="delete_delivery").observe(db_duration)
            delivery_delete_counter.inc()
            if db_delivery:
                active_deliveries_gauge.dec()
            if db_delivery:
                await self.invalidate_delivery_caches(delivery_id, db_delivery.order_id)
            total_duration = time() - start_time
            self.logger.info(f"Delivery deleted in {total_duration:.3f}s (DB: {db_duration:.3f}s)")
            
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при удалении доставки с ID: {delivery_id}, ошибка: {e}")
            return False
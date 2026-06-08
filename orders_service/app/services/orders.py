import asyncio
import logging
import os
import uuid
from typing import Optional

import httpx

from app.models.order import OrderStatus
from app.models.orderItem import OrderItem
from app.repositories.orders import OrderRepository
from app.schemas.orders import OrderCreateSchema, OrderResponseSchema, OrderUpdateStatusSchema
from cache_settings.cache_manager import order_cache, OrderCacheKeys
from kafka_service.kafka.events import OrderCreatedEvent, OrderItemData, OrderStatusChangedEvent, EventType
from datetime import datetime
from kafka_service.kafka.producer import kafka_producer

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8002").rstrip("/")
INTERNAL_CALL_HEADER = os.getenv("INTERNAL_CALL_HEADER", "X-Internal-Token")
INTERNAL_CALL_TOKEN = os.getenv("INTERNAL_CALL_TOKEN", "")


class OrderService:
    """Класс-сервис для управления логики заказов"""
    
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo
        self.logger = logging.getLogger(__name__)
        
    async def invalidate_order_caches(self, order_id: uuid.UUID, user_id: Optional[uuid.UUID] = None):
        """Инвалидация кеша, связанные с заказом"""
        await order_cache.delete(OrderCacheKeys.ORDER_BY_ID.format(order_id=order_id))
        
        if user_id:
            await order_cache.delete(OrderCacheKeys.USER_ORDERS.format(user_id=user_id))
            
        await order_cache.delete_pattern("all_orders:*")
        
        await order_cache.publish_event("order.updated", {
            "order_id": str(order_id),
            "user_id": str(user_id) if user_id else None
        })
    
    async def publish_order_created(self, order_data: dict):
        """Публикация события о создании заказа"""
        try:
            items = [
                OrderItemData(
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    quantity=item["quantity"],
                    price_per_unit=item["price_per_unit"]
                )
                for item in order_data.get("items", [])
            ]
            
            event = OrderCreatedEvent(
                source_service="orders-service",
                correlation_id=str(uuid.uuid4()),
                data=OrderCreatedEvent.Data(
                    order_id=str(order_data["order_id"]),
                    user_id=str(order_data["user_id"]),
                    total_amount=order_data["total_amount"],
                    status=order_data["status"],
                    items=items,
                    created_at=order_data.get("created_at", datetime.now())
                )
            )
            
            await kafka_producer.publish_event("order.events", event, key=str(order_data["order_id"]))
            self.logger.info(f"Published order.created event for order {order_data['order_id']}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish order.created event: {e}")
    
    async def publish_order_status_changed(self, order_id: str, old_status: str, new_status: str, user_id: str):
        """Публикация события об изменении статуса заказа"""
        try:
            event = OrderStatusChangedEvent(
                source_service="orders-service",
                correlation_id=str(uuid.uuid4()),
                data=OrderStatusChangedEvent.Data(
                    order_id=order_id,
                    old_status=old_status,
                    new_status=new_status,
                    updated_at=datetime.now()
                )
            )
            
            await kafka_producer.publish_event("order.events", event, key=order_id)
            self.logger.info(f"Published order.status.changed event for order {order_id}: {old_status} -> {new_status}")
            
        except Exception as e:
            self.logger.error(f"Failed to publish order.status.changed event: {e}")
    
    async def create_order(self, order_create: OrderCreateSchema) -> OrderResponseSchema | None:
        self.logger.info(f"Создание заказа для пользователя {order_create.user_id}")
        
        if not INTERNAL_CALL_TOKEN:
            self.logger.error("INTERNAL_CALL_TOKEN is not configured")
            return None
            
        headers = {INTERNAL_CALL_HEADER: INTERNAL_CALL_TOKEN}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            product_tasks = [
                client.get(
                    f"{GATEWAY_URL}/products/{item.product_id}",
                    headers=headers,
                )
                for item in order_create.items
            ]
            responses = await asyncio.gather(*product_tasks, return_exceptions=True)

        items: list[OrderItem] = []
        for item, response in zip(order_create.items, responses, strict=False):
            if isinstance(response, Exception):
                self.logger.error("Ошибка при запросе продукта %s: %s", item.product_id, response)
                return None
            if response.status_code != 200:
                self.logger.warning(
                    "Продукт не найден или недоступен: %s (status=%s)",
                    item.product_id,
                    response.status_code,
                )
                return None
            payload = response.json()
            items.append(
                OrderItem(
                    product_id=item.product_id,
                    product_name=payload.get("name", ""),
                    quantity=item.quantity,
                    price_per_unit=payload.get("price", 0.0),
                )
            )
        
        db_order = await self.order_repo.create_order(
            user_id=order_create.user_id,
            items=items,
        )
        
        if not db_order:
            return None
        
        await self.publish_order_created(db_order.__dict__)
        
        await self.invalidate_order_caches(db_order.order_id, db_order.user_id)
        
        return OrderResponseSchema.model_validate(db_order)
    
    async def get_order_by_id(self, order_id: uuid.UUID) -> OrderResponseSchema | None:
        self.logger.info(f"Получение заказа по ID: {order_id}")
        
        cache_key = OrderCacheKeys.ORDER_BY_ID.format(order_id=order_id)
        cached_order = await order_cache.get(cache_key)
        
        if cached_order:
            self.logger.info(f"Получаем данные из кеша для {order_id}")
            return OrderResponseSchema(**cached_order)
        
        db_order = await self.order_repo.get_order_by_id(order_id)
        if not db_order:
            return None
        
        order_data = OrderResponseSchema.model_validate(db_order).model_dump()
        await order_cache.set(cache_key, order_data, expire=3600)
        
        return OrderResponseSchema.model_validate(db_order)
    
    async def get_all_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: uuid.UUID | None = None,
        status: OrderStatus | None = None,
    ) -> list[OrderResponseSchema]:
        self.logger.info(
            "Получение всех заказов: skip=%s, limit=%s, user_id=%s, status=%s",
            skip,
            limit,
            user_id,
            status,
        )
        
        if user_id:
            cache_key = OrderCacheKeys.USER_ORDERS.format(user_id=user_id)
            cached_orders = await order_cache.get(cache_key)
            if cached_orders:
                return [OrderResponseSchema(**order) for order in cached_orders]
             
        cache_key = OrderCacheKeys.ALL_ORDERS.format(skip=skip, limit=limit)
        if status:
            cache_key += f":status={status}"
            
        cached_orders = await order_cache.get(cache_key)
        if cached_orders:
            return [OrderResponseSchema(**order) for order in cached_orders]
                   
        db_orders = await self.order_repo.get_all_orders(
            skip=skip,
            limit=limit,
            user_id=user_id,
            status=status,
        )
        orders = [OrderResponseSchema.model_validate(order) for order in db_orders]
        orders_data = [order.model_dump() for order in orders]
        
        ttl = 300 if user_id else 600
        await order_cache.set(cache_key, orders_data, expire=ttl)
        
        return orders
    
    async def update_order_status(self, order_id: uuid.UUID, order_update: OrderUpdateStatusSchema) -> OrderResponseSchema | None:
        self.logger.info(
            "Обновление статуса заказа с ID: %s на новый статус: %s",
            order_id,
            order_update.new_status,
        )
        old_order = await self.order_repo.get_order_by_id(order_id)
        if not old_order:
            return None
        
        db_order = await self.order_repo.update_order_status(order_id, order_update.new_status)
        if not db_order:
            return None
        
        await self.publish_order_status_changed(
            order_id=str(order_id),
            old_status=old_order.status.value,
            new_status=order_update.new_status.value,
            user_id=str(old_order.user_id)
        )
        
        await self.invalidate_order_caches(order_id, old_order.user_id)
        
        await order_cache.publish_event("order.status_changed", {
            "order_id": str(order_id),
            "old_status": old_order.status.value,
            "new_status": order_update.new_status.value,
            "user_id": str(old_order.user_id)
        })
        
        return OrderResponseSchema.model_validate(db_order)
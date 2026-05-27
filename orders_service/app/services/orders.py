import asyncio
import logging
import os
import uuid

import httpx

from app.models.order import OrderStatus
from app.models.orderItem import OrderItem
from app.repositories.orders import OrderRepository
from app.schemas.orders import OrderCreateSchema, OrderResponseSchema, OrderUpdateStatusSchema

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8002").rstrip("/")
INTERNAL_CALL_HEADER = os.getenv("INTERNAL_CALL_HEADER", "X-Internal-Call")
INTERNAL_CALL_VALUE = os.getenv("INTERNAL_CALL_VALUE", "true")

class OrderService:
    """Класс-сервис для управления логики заказов, обеспечивающий взаимодействие между репозиторием и API."""
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo
        self.logger = logging.getLogger(__name__)
    
    async def create_order(self, order_create: OrderCreateSchema) -> OrderResponseSchema | None:
        self.logger.info(f"Создание заказа для пользователя {order_create.user_id}")
        headers = {INTERNAL_CALL_HEADER: INTERNAL_CALL_VALUE}
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
        return OrderResponseSchema.model_validate(db_order)
    
    async def get_order_by_id(self, order_id: uuid.UUID) -> OrderResponseSchema | None:
        self.logger.info(f"Получение заказа по ID: {order_id}")
        db_order = await self.order_repo.get_order_by_id(order_id)
        if not db_order:
            return None
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
        db_orders = await self.order_repo.get_all_orders(
            skip=skip,
            limit=limit,
            user_id=user_id,
            status=status,
        )
        return [OrderResponseSchema.model_validate(order) for order in db_orders]
    
    async def update_order_status(self, order_id: uuid.UUID, order_update: OrderUpdateStatusSchema) -> OrderResponseSchema | None:
        self.logger.info(
            "Обновление статуса заказа с ID: %s на новый статус: %s",
            order_id,
            order_update.new_status,
        )
        try:
            db_order = await self.order_repo.update_order_status(order_id, order_update.new_status)
        except ValueError:
            return None
        return OrderResponseSchema.model_validate(db_order)
import logging
import uuid

from app.models.order import OrderStatus
from app.models.orderItem import OrderItem
from app.repositories.orders import OrderRepository
from app.schemas.orders import OrderCreateSchema, OrderResponseSchema, OrderUpdateStatusSchema

class OrderService:
    """Класс-сервис для управления логики заказов, обеспечивающий взаимодействие между репозиторием и API."""
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo
        self.logger = logging.getLogger(__name__)
    
    async def create_order(self, order_create: OrderCreateSchema) -> OrderResponseSchema:
        self.logger.info(f"Создание заказа для пользователя {order_create.user_id}")
        items = [
            OrderItem(
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                price_per_unit=item.price_per_unit,
            )
            for item in order_create.items
        ]
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
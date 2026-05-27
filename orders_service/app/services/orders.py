import uuid 
import logging

from app.repositories.orders import OrderRepository
from app.schemas.order import OrderCreateSchema, OrderResponseSchema, OrderUpdateStatusSchema

class OrderService:
    """Класс-сервис для управления логики заказов, обеспечивающий взаимодействие между репозиторием и API."""
    def __init__(self, order_repo: OrderRepository):
        self.order_repo = order_repo
        self.logger = logging.getLogger(__name__)
    
    async def create_order(self, order_create: OrderCreateSchema) -> OrderResponseSchema:
        self.logger.info(f"Создание заказа для пользователя {order_create.user_id}")
        db_order = await self.order_repo.create_order(
            user_id=order_create.user_id,
            items=order_create.items,
        )
        return OrderResponseSchema.model_validate(db_order)
    
    async def get_order_by_id(self, order_id: uuid.UUID) -> OrderResponseSchema | None:
        self.logger.info(f"Получение заказа по ID: {order_id}")
        db_order = await self.order_repo.get_order_by_id(order_id)
        if not db_order:
            return None
        return OrderResponseSchema.model_validate(db_order)
    
    async def get_all_orders(self, skip: int = 0, limit: int = 100, filter = None) -> list[OrderResponseSchema]:
        self.logger.info(f"Получение всех заказов: skip={skip}, limit={limit}, по фильтру: {filter}")
        db_orders = await self.order_repo.get_all_orders(skip=skip, limit=limit, filter=filter)
        return [OrderResponseSchema.model_validate(order) for order in db_orders]
    
    async def update_order_status(self, order_id: uuid.UUID, order_update: OrderUpdateStatusSchema) -> OrderResponseSchema | None:
        self.logger.info(f"Обновление статуса заказа с ID: {order_id} на новый статус: {order_update.status}")
        try:
            db_order = await self.order_repo.update_order_status(order_id, order_update.status)
        except ValueError:
            return None
        return OrderResponseSchema.model_validate(db_order)
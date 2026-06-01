import logging
import uuid
from typing import List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderStatus
from app.models.orderItem import OrderItem

class OrderRepository:
    """Класс-репозиторий для управления данными о заказах"""
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    async def get_all_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: uuid.UUID | None = None,
        status: OrderStatus | None = None,
    ) -> List[Order]:
        self.logger.info("Получение всех заказов")
        query = select(Order).offset(skip).limit(limit)
        if user_id is not None:
            query = query.where(Order.user_id == user_id)
        if status is not None:
            query = query.where(Order.status == status)
        query = query.options(selectinload(Order.items))
        result = await self.db.scalars(query)  # ❌ Уберите try/except
        return list(result)
    
    async def get_order_by_id(self, order_id: uuid.UUID) -> Order | None:
        self.logger.info(f"Получение заказа по ID: {order_id}")
        try:
            query = select(Order).where(Order.order_id == order_id).options(selectinload(Order.items))
            result = await self.db.scalar(query)
        except Exception as e:
            self.logger.error(f"Ошибка при получении заказа по ID {order_id}, ошибка: {e}")
            result = None
        return result
    
    async def create_order(self, *, user_id: uuid.UUID, items: List[OrderItem]) -> Order | None:
        self.logger.info(f"Создание заказа для пользователя: {user_id}")
        try:
            items = items or []
            total_amount = sum(item.price_per_unit * item.quantity for item in items)
            order = Order(
                user_id=user_id,
                status=OrderStatus.PENDING,
                total_amount=total_amount,
            )
            order.items = items
            self.db.add(order)
            await self.db.commit()
            
            query = select(Order).where(Order.order_id == order.order_id).options(
            selectinload(Order.items)
            )
            result = await self.db.execute(query)
            order = result.scalar_one()
        except Exception as e:
            self.logger.error(f"Ошибка при создании заказа, ошибка: {e}")
            await self.db.rollback()
            order = None
        return order
    
    async def update_order_status(self, order_id: uuid.UUID, new_status: OrderStatus) -> Order | None:
        self.logger.info(f"Обновление статуса заказа (order_id={order_id}, new_status={new_status})")
        try:
            await self.db.execute(
                update(Order)
                .where(Order.order_id == order_id)
                .values(status=new_status)
            )
            await self.db.commit()
            
            query = select(Order).where(Order.order_id == order_id).options(selectinload(Order.items))
            updated_order = await self.db.scalar(query)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении статуса заказа (order_id={order_id}), ошибка: {e}")
            await self.db.rollback()
            updated_order = None
        return updated_order
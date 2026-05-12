import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.orders import OrderRepository
from app.services.orders import OrderService

logger = logging.getLogger(__name__)

"""Вспомогательные методы для сервиса заказов, обеспечивающие внедрение зависимостей."""

async def get_async_db():
    async with AsyncSessionLocal() as db:
        logger.info("Получение асинхронной сессии базы данных...")
        yield db
        logger.info("Асинхронная сессия базы данных закрыта.")
        
def get_order_repository(db: AsyncSession = Depends(get_async_db)) -> OrderRepository:
    logger.info("Получение репозитория заказов...")
    return OrderRepository(db=db)

def get_order_service(order_repo: OrderRepository = Depends(get_order_repository)) -> OrderService:
    logger.info("Получение сервиса заказов...")
    return OrderService(order_repo=order_repo)

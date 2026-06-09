from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import AsyncSessionLocal
from app.repositories.delivery import DeliveryRepository
from app.services.delivery import DeliveryService

logger = logging.getLogger(__name__)

"""Вспомогательные методы для сервиса доставки, обеспечивающие внедрение зависимостей."""

async def get_async_db():
    async with AsyncSessionLocal() as db:
        logger.info("Getting async database session...")
        yield db
        logger.info("Async database session closed.")
        
def get_delivery_repository(db: AsyncSession = Depends(get_async_db)) -> DeliveryRepository:
    logger.info("Getting delivery repository...")
    return DeliveryRepository(db=db)

def get_delivery_service(delivery_repo: DeliveryRepository = Depends(get_delivery_repository)) -> DeliveryService:
    logger.info("Getting delivery service...")
    return DeliveryService(delivery_repo=delivery_repo)

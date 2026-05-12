from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import AsyncSessionLocal
from app.repositories.delivery import DeliveryRepository
from app.services.delivery import DeliveryService

logger = logging.getLogger(__name__)

async def get_async_db():
    async with AsyncSessionLocal() as db:
        logger.info("Получение асинхронной сессии базы данных...")
        yield db
        logger.info("Асинхронная сессия базы данных закрыта.")
        
def get_delivery_repository(db: AsyncSession = Depends(get_async_db)) -> DeliveryRepository:
    logger.info("Получение репозитория доставки...")
    return DeliveryRepository(db=db)

def get_delivery_service(delivery_repo: DeliveryRepository = Depends(get_delivery_repository)) -> DeliveryService:
    logger.info("Получение сервиса доставки...")
    return DeliveryService(delivery_repo=delivery_repo)

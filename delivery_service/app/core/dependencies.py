from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.delivery import DeliveryRepository
from app.services.delivery import DeliveryService

async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db
        
def get_delivery_repository(db: AsyncSession = Depends(get_async_db)) -> DeliveryRepository:
    return DeliveryRepository(db=db)

def get_delivery_service(delivery_repo: DeliveryRepository = Depends(get_delivery_repository)) -> DeliveryService:
    return DeliveryService(delivery_repo=delivery_repo)

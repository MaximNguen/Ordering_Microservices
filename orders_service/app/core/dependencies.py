from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.orders import OrderRepository
from app.services.orders import OrderService

async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db
        
def get_order_repository(db: AsyncSession = Depends(get_async_db)) -> OrderRepository:
    return OrderRepository(db=db)

def get_order_service(order_repo: OrderRepository = Depends(get_order_repository)) -> OrderService:
    return OrderService(order_repo=order_repo)

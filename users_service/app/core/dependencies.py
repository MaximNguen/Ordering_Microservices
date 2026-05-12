from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.users import UserRepository
from app.services.users import UserService

async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db
        
def get_user_repository(db: AsyncSession = Depends(get_async_db)) -> UserRepository:
    return UserRepository(db=db)

def get_user_service(user_repo: UserRepository = Depends(get_user_repository)) -> UserService:
    return UserService(user_repo=user_repo)

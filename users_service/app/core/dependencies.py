from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import AsyncSessionLocal
from app.repositories.users import UserRepository
from app.services.users import UserService

logger = logging.getLogger(__name__)

"""Вспомогательные методы для сервиса пользователей, обеспечивающие внедрение зависимостей."""

async def get_async_db():
    async with AsyncSessionLocal() as db:
        logger.info("Получение асинхронной сессии базы данных...")
        yield db
        logger.info("Асинхронная сессия базы данных закрыта.")
        
def get_user_repository(db: AsyncSession = Depends(get_async_db)) -> UserRepository:
    logger.info("Получение репозитория пользователей...")
    return UserRepository(db=db)

def get_user_service(user_repo: UserRepository = Depends(get_user_repository)) -> UserService:
    logger.info("Получение сервиса пользователей...")
    return UserService(user_repo=user_repo)

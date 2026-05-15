from sqlalchemy import select, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models import User

logger = logging.getLogger(__name__)

class UserRepository:
    """Репозиторий для работы с пользователями в базе данных."""
    
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Получить пользователя по его ID."""
        logger.info(f"Получение пользователя с ID: {user_id}")
        try:
            res = await self.db.scalar(select(User).where(User.user_id == user_id, User.is_active == True))
            if res is None:
                logger.warning(f"Пользователь с ID {user_id} не найден или неактивен")
                raise HTTPException(status_code=404, detail="Пользователь не найден")
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            raise HTTPException(status_code=500, detail="Ошибка сервера")
        logger.info(f"Пользователь найден: {res}")
        return res
    
    async def get_all_users(self) -> list[User]:
        """Получить всех активных пользователей."""
        logger.info("Получение всех активных пользователей")
        try:
            res = await self.db.scalars(select(User).where(User.is_active == True))
            logger.info(f"Найдены пользователи: {res.all()}")
            return res.all()
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            raise HTTPException(status_code=500, detail="Ошибка сервера")
        
    
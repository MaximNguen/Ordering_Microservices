import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.models import User

logger = logging.getLogger(__name__)

class UserRepository:
    """Репозиторий для работы с пользователями в базе данных."""
    
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_user_by_email(self, email: str) -> User | None:
        """Получить пользователя по его email."""
        logger.info(f"Получение пользователя с email: {email}")
        try:
            res = await self.db.scalar(select(User).where(User.email == email, User.is_active == True))
            if res is None:
                logger.warning(f"Пользователь с email {email} не найден или неактивен")
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None
        logger.info(f"Пользователь найден: {res}")
        return res

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """Получить пользователя по его идентификатору."""
        logger.info(f"Получение пользователя с id: {user_id}")
        try:
            res = await self.db.scalar(
                select(User).where(User.user_id == user_id, User.is_active == True)
            )
            if res is None:
                logger.warning(f"Пользователь с id {user_id} не найден или неактивен")
                return None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None
        logger.info(f"Пользователь найден: {res}")
        return res
    
    async def get_all_users(self) -> list[User]:
        """Получить всех активных пользователей."""
        logger.info("Получение всех активных пользователей")
        try:
            res = await self.db.scalars(select(User).where(User.is_active == True))
            users = res.all()
            logger.info(f"Найдены пользователи: {len(users)}")
            return users
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            return None

    async def create_user(self, user: User) -> User:
        """Создать нового пользователя."""
        logger.info(f"Создание нового пользователя с email: {user.email}")
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"Пользователь успешно создан: {user}")
            return user
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            await self.db.rollback()
            return None
import logging
import uuid

import jwt
from fastapi import HTTPException, status

from app.repositories.users import UserRepository
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.user import UserCreate, User as UserSchema
from app.models.user import User as UserModel, UserRole
from users_service.config import ALGORITHM, SECRET_KEY

class UserService:
    """Сервис для управления пользователями, предоставляющий бизнес-логику для операций с пользователями."""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        self.logger = logging.getLogger(__name__)

    def _normalize_role(self, role: str | None) -> UserRole:
        if not role:
            return UserRole.CUSTOMER
        role_value = role.lower()
        if role_value == "buyer":
            role_value = "customer"
        try:
            return UserRole(role_value)
        except ValueError:
            return UserRole.CUSTOMER

    def _to_user_schema(self, user: UserModel) -> UserSchema:
        role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        return UserSchema(
            id=user.user_id,
            email=user.email,
            is_active=user.is_active,
            role=role_value,
        )

    def _parse_user_id(self, value: object) -> uuid.UUID | None:
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError:
                return None
        return None

    async def create_user(self, user_create: UserCreate) -> UserSchema | None:
        """Создать нового пользователя."""
        self.logger.info(f"Создание нового пользователя с email: {user_create.email}")
        try:
            password_hash = hash_password(user_create.password)
            role_enum = self._normalize_role(user_create.role)
            new_user = await self.user_repository.create_user(
                UserModel(
                    email=user_create.email,
                    login=user_create.login,
                    password_hash=password_hash,
                    role=role_enum,
                    name=user_create.name,
                )
            )
            
            if new_user is None:
                return None
            self.logger.info(f"Пользователь успешно создан: {new_user}")
            return self._to_user_schema(new_user)
        except Exception as e:
            self.logger.error(f"Ошибка при создании пользователя: {e}")
            return None
        
    async def login(self, email: str, password: str) -> UserSchema | None:
        """Авторизация пользователя по email и паролю."""
        self.logger.info(f"Авторизация пользователя с email: {email}")
        try:
            user = await self.user_repository.get_user_by_email(email)
            if user and verify_password(password, user.password_hash):
                self.logger.info(f"Пользователь успешно авторизован: {user}")
                return self._to_user_schema(user)
            else:
                self.logger.warning(f"Неверные учетные данные для email: {email}")
                return None
        except Exception as e:
            self.logger.error(f"Ошибка при авторизации пользователя: {e}")
            return None
        
    async def get_user_by_email(self, email: str) -> UserSchema | None:
        """Получить пользователя по его email."""
        self.logger.info(f"Получение пользователя с email: {email}")
        try:
            user = await self.user_repository.get_user_by_email(email)
            if user is None:
                return None
            self.logger.info(f"Пользователь найден: {user}")
            return self._to_user_schema(user)
        except Exception as e:
            self.logger.error(f"Ошибка при получении пользователя: {e}")
            return None
    
    async def get_all_users(self) -> list[UserSchema] | None:
        """Получить всех пользователей."""
        self.logger.info("Получение всех пользователей")
        try:
            users = await self.user_repository.get_all_users()
            if users is None:
                return None
            self.logger.info(f"Найдено пользователей: {len(users)}")
            return [self._to_user_schema(user) for user in users]
        except Exception as e:
            self.logger.error(f"Ошибка при получении пользователей: {e}")
            return None

    async def refresh_token(self, refresh_token: str) -> dict:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id_value = payload.get("id")
            token_type: str | None = payload.get("token_type")
            if token_type != "refresh":
                raise credentials_exception
            user_id = self._parse_user_id(user_id_value)
            if user_id is None:
                raise credentials_exception
        except jwt.ExpiredSignatureError:
            raise credentials_exception
        except jwt.PyJWTError:
            raise credentials_exception

        user = await self.user_repository.get_user_by_id(user_id)
        if user is None:
            raise credentials_exception

        role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        new_refresh_token = create_refresh_token(
            data={"sub": user.email, "role": role_value, "id": str(user.user_id)}
        )
        return {"refresh_token": new_refresh_token, "token_type": "bearer"}

    async def access_token(self, refresh_token: str) -> dict:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id_value = payload.get("id")
            token_type: str | None = payload.get("token_type")
            if token_type != "refresh":
                raise credentials_exception
            user_id = self._parse_user_id(user_id_value)
            if user_id is None:
                raise credentials_exception
        except jwt.ExpiredSignatureError:
            raise credentials_exception
        except jwt.PyJWTError:
            raise credentials_exception

        user = await self.user_repository.get_user_by_id(user_id)
        if user is None:
            raise credentials_exception

        role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        access_token = create_access_token(
            data={
                "sub": user.email,
                "role": role_value,
                "id": str(user.user_id),
                "token_type": "access",
            }
        )
        return {"access_token": access_token, "token_type": "bearer"}
import uuid
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class User(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    role: str
    model_config = ConfigDict(from_attributes=True)
    
class UserCreate(BaseModel):
    email: EmailStr
    login: str = Field(..., description="Логин пользователя")
    password: str = Field(min_length=6, description="Пароль (минимум 6 символов)")
    role: str = Field(default="buyer", description="Роль пользователя (по умолчанию 'buyer')")
    name: str = Field(..., description="Имя пользователя")
    model_config = ConfigDict(from_attributes=True)
    
class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh токен для получения нового access токена")

class UserWithTokens(BaseModel):
    user: User
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
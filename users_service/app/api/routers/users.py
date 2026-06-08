from fastapi import HTTPException, Request, status, Depends, APIRouter

from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.users import UserService
from app.schemas.user import RefreshTokenRequest, UserCreate, User as UserSchema, UserWithTokens
from app.core.dependencies import get_user_service
from app.utils.auth import get_current_user
    
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/", response_model=UserWithTokens, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_user(
    request: Request,
    user_create: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """Создать нового пользователя на основе данных из запроса."""
    result = await user_service.create_user(user_create)
    if not result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ошибка при создании пользователя")
    return result

@router.post("/token")
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), user_service: UserService = Depends(get_user_service)):
    """Аутентификация пользователя и выдача JWT токенов."""
    token_response = await user_service.login(form_data.username, form_data.password)
    if not token_response:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверные учетные данные")
    return token_response

@router.post("/refresh-token")
@limiter.limit("10/minute")
async def refresh_token(
    body: RefreshTokenRequest,
    request: Request,
    _current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Обновление refresh токена по действующему refresh токену."""
    return await user_service.refresh_token(body.refresh_token)

@router.post("/access-token")
@limiter.limit("10/minute")
async def access_token(
    request: Request,
    body: RefreshTokenRequest,
    _current_user=Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """Получение access токена по действующему refresh токену."""
    return await user_service.access_token(body.refresh_token)

@router.get("/me", response_model=UserSchema)
@limiter.limit("50/minute")
async def get_me(request: Request, current_user=Depends(get_current_user)):
    """Получить данные текущего пользователя по access токену."""
    return current_user
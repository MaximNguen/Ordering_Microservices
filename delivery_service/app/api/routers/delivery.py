import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from app.core.dependencies import get_delivery_service
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from app.services.delivery import DeliveryService
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
bearer_scheme = HTTPBearer(auto_error=False)
INTERNAL_CALL_HEADER = os.getenv("INTERNAL_CALL_HEADER", "X-Internal-Token")
INTERNAL_CALL_TOKEN = os.getenv("INTERNAL_CALL_TOKEN", "")
SECRET_KEY = os.getenv("SECRET_KEY", "")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


def require_service_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> None:
    if INTERNAL_CALL_TOKEN and request.headers.get(INTERNAL_CALL_HEADER) == INTERNAL_CALL_TOKEN:
        return
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth is not configured",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

router = APIRouter(
    prefix="/deliveries",
    tags=["deliveries"],
    dependencies=[Depends(require_service_auth)],
)


@router.get("/", response_model=list[DeliveryResponse], status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_all_deliveries(
    skip: int = 0,
    limit: int = 100,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Получить список всех доставок с поддержкой пагинации."""
    return await delivery_service.get_all_deliveries(skip=skip, limit=limit)

@router.post("/", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_delivery(
    delivery_create: DeliveryCreate,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Создать новую доставку на основе данных из запроса."""
    delivery = await delivery_service.create_delivery(delivery_create)
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return delivery

@router.get("/{delivery_id}", response_model=DeliveryResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_delivery_by_id(
    delivery_id: uuid.UUID,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Получить информацию о доставке по ее уникальному идентификатору."""
    delivery = await delivery_service.get_delivery_by_id(delivery_id)
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Доставка не найдена")
    return delivery

@router.delete("/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute")
async def delete_delivery(
    delivery_id: uuid.UUID,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Удалить доставку по ее уникальному идентификатору."""
    delivery = await delivery_service.get_delivery_by_id(delivery_id)
    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Доставка не найдена")
    await delivery_service.delete_delivery(delivery_id)
    
@router.put("/{delivery_id}", response_model=DeliveryResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def update_delivery(
    delivery_id: uuid.UUID,
    delivery_update: DeliveryUpdate,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Обновить информацию о доставке по ее уникальному идентификатору."""
    updated_delivery = await delivery_service.update_delivery(delivery_id, delivery_update)
    if not updated_delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Доставка не найдена")
    return updated_delivery
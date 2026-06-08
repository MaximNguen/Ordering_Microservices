import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status as status_fastapi
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.dependencies import get_order_service
from app.models.order import OrderStatus
from app.schemas.orders import OrderCreateSchema, OrderResponseSchema, OrderUpdateStatusSchema
from app.services.orders import OrderService

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
            status_code=status_fastapi.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status_fastapi.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth is not configured",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("token_type") != "access":
            raise HTTPException(
                status_code=status_fastapi.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status_fastapi.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Depends(require_service_auth)],
)

@router.get("/", response_model=list[OrderResponseSchema], status_code=status_fastapi.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_all_orders(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    user_id: uuid.UUID | None = None,
    status: OrderStatus | None = None,
    order_service: OrderService = Depends(get_order_service)
):
    """Получить список всех заказов с поддержкой пагинации."""
    results = await order_service.get_all_orders(
        skip=skip,
        limit=limit,
        user_id=user_id,
        status=status,
    )
    if not results:
        raise HTTPException(status_code=status_fastapi.HTTP_404_NOT_FOUND, detail="Заказы не найдены")
    return results

@router.post("/", response_model=OrderResponseSchema, status_code=status_fastapi.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_order(
    request: Request,
    order_create: OrderCreateSchema,
    order_service: OrderService = Depends(get_order_service)
):
    """Создать новый заказ на основе данных из запроса."""
    order = await order_service.create_order(order_create)
    if not order:
        raise HTTPException(status_code=status_fastapi.HTTP_400_BAD_REQUEST, detail="Ошибка при создании заказа")
    return order

@router.get("/{order_id}", response_model=OrderResponseSchema, status_code=status_fastapi.HTTP_200_OK)
@limiter.limit("10/minute")
async def get_order(
    request: Request,
    order_id: uuid.UUID,
    order_service: OrderService = Depends(get_order_service)
):
    """Получить информацию о конкретном заказе по его ID."""
    order = await order_service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=status_fastapi.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return order

@router.put("/{order_id}", response_model=OrderResponseSchema, status_code=status_fastapi.HTTP_200_OK)
@limiter.limit("10/minute")
async def update_order_status(
    request: Request,
    order_id: uuid.UUID,
    order_update: OrderUpdateStatusSchema,
    order_service: OrderService = Depends(get_order_service)
):
    """Обновить статус существующего заказа по его ID."""
    updated_order = await order_service.update_order_status(order_id, order_update)
    if not updated_order:
        raise HTTPException(status_code=status_fastapi.HTTP_404_NOT_FOUND, detail="Заказ не найден или ошибка при обновлении статуса")
    return updated_order
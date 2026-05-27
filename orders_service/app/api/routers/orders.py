import uuid

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer

from app.core.dependencies import get_order_service
from app.models.order import OrderStatus
from app.schemas.orders import OrderCreateSchema, OrderResponseSchema, OrderUpdateStatusSchema
from app.services.orders import OrderService

bearer_scheme = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    dependencies=[Security(bearer_scheme)],
)

@router.get("/", response_model=list[OrderResponseSchema], status_code=status.HTTP_200_OK)
async def get_all_orders(
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказы не найдены")
    return results

@router.post("/", response_model=OrderResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_create: OrderCreateSchema,
    order_service: OrderService = Depends(get_order_service)
):
    """Создать новый заказ на основе данных из запроса."""
    order = await order_service.create_order(order_create)
    if not order:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ошибка при создании заказа")
    return order

@router.get("/{order_id}", response_model=OrderResponseSchema, status_code=status.HTTP_200_OK)
async def get_order(
    order_id: uuid.UUID,
    order_service: OrderService = Depends(get_order_service)
):
    """Получить информацию о конкретном заказе по его ID."""
    order = await order_service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return order

@router.put("/{order_id}", response_model=OrderResponseSchema, status_code=status.HTTP_200_OK)
async def update_order_status(
    order_id: uuid.UUID,
    order_update: OrderUpdateStatusSchema,
    order_service: OrderService = Depends(get_order_service)
):
    """Обновить статус существующего заказа по его ID."""
    updated_order = await order_service.update_order_status(order_id, order_update)
    if not updated_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден или ошибка при обновлении статуса")
    return updated_order
import uuid

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer

from app.core.dependencies import get_delivery_service
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse
from app.services.delivery import DeliveryService

bearer_scheme = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/deliveries",
    tags=["deliveries"],
    dependencies=[Security(bearer_scheme)],
)

@router.get("/", response_model=list[DeliveryResponse], status_code=status.HTTP_200_OK)
async def get_all_deliveries(
    skip: int = 0,
    limit: int = 100,
    delivery_service: DeliveryService = Depends(get_delivery_service)
):
    """Получить список всех доставок с поддержкой пагинации."""
    return await delivery_service.get_all_deliveries(skip=skip, limit=limit)

@router.post("/", response_model=DeliveryResponse, status_code=status.HTTP_201_CREATED)
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
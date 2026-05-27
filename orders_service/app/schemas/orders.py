from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import datetime
import uuid

from app.models.order import OrderStatus

class OrderItemSchema(BaseModel):
    """Схема для элемента заказа, используемая для валидации данных при создании и обновлении заказа."""
    model_config = ConfigDict(from_attributes=True)
    product_id: uuid.UUID
    product_name: str
    quantity: int
    price_per_unit: float
    
class OrderCreateSchema(BaseModel):
    """Схема для создания нового заказа, определяющая необходимые поля и их типы."""
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    items: List[OrderItemSchema]
    
class OrderUpdateStatusSchema(BaseModel):
    """Схема для обновления статуса заказа, определяющая допустимые значения статуса."""
    model_config = ConfigDict(from_attributes=True)
    new_status: OrderStatus

class OrderResponseSchema(BaseModel):
    """Схема для ответа API, содержащая информацию о заказе."""
    model_config = ConfigDict(from_attributes=True)
    order_id: uuid.UUID
    user_id: uuid.UUID
    items: List[OrderItemSchema]
    total_amount: float
    created_at: datetime
    status: OrderStatus
from pydantic import BaseModel, Field
from pydantic import ConfigDict
import uuid
from datetime import datetime

from app.models.delivery import DeliveryStatus

class DeliveryCreate(BaseModel):
    """Класс-схема для создания новой доставки, определяющий необходимые поля и их типы."""
    model_config = ConfigDict(from_attributes=True)
    
    order_id: uuid.UUID = Field(..., description="ID заказа, для которого создается доставка")
    delivery_person_id: uuid.UUID | None = Field(None, description="ID курьера, если назначен")
    address: str = Field(..., description="Адрес доставки")
    scheduled_time: datetime | None = Field(None, description="Запланированное время доставки в формате ISO 8601")
    delivery_fee: float = Field(0.0, description="Стоимость доставки")
    
class DeliveryUpdate(BaseModel):
    """Класс-схема для обновления информации о доставке, определяющий поля, которые могут быть изменены."""
    model_config = ConfigDict(from_attributes=True)
    
    status: DeliveryStatus | None = Field(None, description="Новый статус доставки")
    
class DeliveryResponse(BaseModel):
    """Класс-схема для ответа API, содержащий информацию о доставке."""
    model_config = ConfigDict(from_attributes=True)
    
    delivery_id: uuid.UUID = Field(..., description="Уникальный идентификатор доставки")
    order_id: uuid.UUID = Field(..., description="ID заказа, связанного с доставкой")
    delivery_person_id: uuid.UUID | None = Field(None, description="ID курьера, если назначен")
    status: DeliveryStatus = Field(..., description="Текущий статус доставки")
    address: str = Field(..., description="Адрес доставки")
    scheduled_time: datetime | None = Field(None, description="Запланированное время доставки в формате ISO 8601")
    actual_delivery_time: datetime | None = Field(None, description="Фактическое время доставки в формате ISO 8601")
    delivery_fee: float = Field(0.0, description="Стоимость доставки")
    created_at: datetime = Field(..., description="Время создания записи о доставке в формате ISO 8601")
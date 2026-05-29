from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
import uuid


class EventType(str, Enum):
    ORDER_CREATED = "order.created"
    ORDER_STATUS_CHANGED = "order.status.changed"
    DELIVERY_CREATED = "delivery.created"
    DELIVERY_STATUS_CHANGED = "delivery.status.changed"
    DELIVERY_UPDATED = "delivery.updated"
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"


class BaseEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
    source_service: str
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    data: Dict[str, Any]


class OrderItemData(BaseModel):
    """Схема для элемента заказа в событии"""
    product_id: str
    product_name: str
    quantity: int
    price_per_unit: float


class OrderCreatedEvent(BaseEvent):
    """Событие создания заказа"""
    event_type: EventType = EventType.ORDER_CREATED
    
    class Data(BaseModel):
        order_id: str
        user_id: str
        total_amount: float
        status: str  # OrderStatus как строка
        items: List[OrderItemData]
        created_at: datetime
        
    data: Data


class OrderStatusChangedEvent(BaseEvent):
    """Событие изменения статуса заказа"""
    event_type: EventType = EventType.ORDER_STATUS_CHANGED
    
    class Data(BaseModel):
        order_id: str
        old_status: str
        new_status: str
        updated_at: datetime
        
    data: Data


class DeliveryCreatedEvent(BaseEvent):
    """Событие создания доставки"""
    event_type: EventType = EventType.DELIVERY_CREATED
    
    class Data(BaseModel):
        delivery_id: str
        order_id: str
        address: str
        status: str
        delivery_fee: float
        scheduled_time: Optional[datetime] = None
        created_at: datetime
        
    data: Data


class DeliveryStatusChangedEvent(BaseEvent):
    """Событие изменения статуса доставки"""
    event_type: EventType = EventType.DELIVERY_STATUS_CHANGED
    
    class Data(BaseModel):
        delivery_id: str
        order_id: str
        old_status: str
        new_status: str
        delivery_person_id: Optional[str] = None
        actual_delivery_time: Optional[datetime] = None
        updated_at: datetime
        
    data: Data


class DeliveryUpdatedEvent(BaseEvent):
    """Событие обновления доставки (общее)"""
    event_type: EventType = EventType.DELIVERY_UPDATED
    
    class Data(BaseModel):
        delivery_id: str
        order_id: str
        updates: Dict[str, Any]
        updated_at: datetime
        
    data: Data


class ProductCreatedEvent(BaseEvent):
    """Событие создания продукта"""
    event_type: EventType = EventType.PRODUCT_CREATED
    
    class Data(BaseModel):
        product_id: str
        name: str
        description: Optional[str] = None
        price: float
        created_at: datetime
        
    data: Data


class ProductUpdatedEvent(BaseEvent):
    """Событие обновления продукта"""
    event_type: EventType = EventType.PRODUCT_UPDATED
    
    class Data(BaseModel):
        product_id: str
        name: Optional[str] = None
        description: Optional[str] = None
        price: Optional[float] = None
        updated_at: datetime
        
    data: Data
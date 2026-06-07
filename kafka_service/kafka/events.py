from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List, Type, Union
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
    product_id: str
    product_name: str
    quantity: int
    price_per_unit: float


class OrderCreatedEvent(BaseEvent):
    event_type: EventType = EventType.ORDER_CREATED
    
    class Data(BaseModel):
        order_id: str
        user_id: str
        total_amount: float
        status: str
        items: List[OrderItemData]
        created_at: datetime
        
    data: Data
    
    def model_dump(self, **kwargs) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        if isinstance(data.get('data'), dict):
            return data
        return data


class OrderStatusChangedEvent(BaseEvent):
    event_type: EventType = EventType.ORDER_STATUS_CHANGED
    
    class Data(BaseModel):
        order_id: str
        old_status: str
        new_status: str
        updated_at: datetime
        
    data: Data


class DeliveryCreatedEvent(BaseEvent):
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
    event_type: EventType = EventType.DELIVERY_UPDATED
    
    class Data(BaseModel):
        delivery_id: str
        order_id: str
        updates: Dict[str, Any]
        updated_at: datetime
        
    data: Data


class ProductCreatedEvent(BaseEvent):
    event_type: EventType = EventType.PRODUCT_CREATED
    
    class Data(BaseModel):
        product_id: str
        name: str
        description: Optional[str] = None
        price: float
        created_at: datetime
        
    data: Data


class ProductUpdatedEvent(BaseEvent):
    event_type: EventType = EventType.PRODUCT_UPDATED
    
    class Data(BaseModel):
        product_id: str
        name: Optional[str] = None
        description: Optional[str] = None
        price: Optional[float] = None
        updated_at: datetime
        
    data: Data
    
class DeliveryResponseEvent(BaseEvent):
    """Событие ответа от сервиса доставки"""
    event_type: EventType = EventType.DELIVERY_RESPONSE
    data: Dict[str, Any]

def event_from_dict(data: Dict[str, Any]) -> BaseEvent:
    """Создает конкретный объект события из словаря"""
    event_type = data.get("event_type")
    
    event_classes = {
        EventType.ORDER_CREATED: OrderCreatedEvent,
        EventType.ORDER_STATUS_CHANGED: OrderStatusChangedEvent,
        EventType.DELIVERY_CREATED: DeliveryCreatedEvent,
        EventType.DELIVERY_STATUS_CHANGED: DeliveryStatusChangedEvent,
        EventType.DELIVERY_UPDATED: DeliveryUpdatedEvent,
        EventType.PRODUCT_CREATED: ProductCreatedEvent,
        EventType.PRODUCT_UPDATED: ProductUpdatedEvent,
    }
    
    event_class = event_classes.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown event type: {event_type}")
    
    return event_class(**data)
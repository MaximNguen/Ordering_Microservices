import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer

from app.services.delivery import DeliveryService
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate
from kafka_service.kafka.events import (
    DeliveryCreatedEvent, DeliveryUpdatedEvent, 
    DeliveryStatusChangedEvent, EventType
)
from kafka_service.kafka.producer import kafka_producer
from datetime import datetime

logger = logging.getLogger(__name__)


class DeliveryKafkaHandlers:
    """Обработчики Kafka событий для доставки"""
    
    def __init__(self, delivery_service: DeliveryService):
        self.delivery_service = delivery_service
        
    async def publish_delivery_created(self, delivery_data: Dict[str, Any]):
        """Публикация события о создании доставки"""
        try:
            event = DeliveryCreatedEvent(
                source_service="delivery-service",
                correlation_id=str(uuid.uuid4()),
                data=DeliveryCreatedEvent.Data(
                    delivery_id=str(delivery_data["delivery_id"]),
                    order_id=str(delivery_data["order_id"]),
                    address=delivery_data["address"],
                    status=delivery_data["status"],
                    delivery_fee=delivery_data.get("delivery_fee", 0.0),
                    scheduled_time=delivery_data.get("scheduled_time"),
                    created_at=datetime.now()
                )
            )
            
            await kafka_producer.publish_event("delivery.events", event, key=str(delivery_data["order_id"]))
            logger.info(f"Published delivery.created event for delivery {delivery_data['delivery_id']}")
            
        except Exception as e:
            logger.error(f"Failed to publish delivery.created event: {e}")
    
    async def publish_delivery_updated(self, delivery_id: str, order_id: str, old_status: str, new_status: str):
        """Публикация события об обновлении доставки"""
        try:
            event = DeliveryStatusChangedEvent(
                source_service="delivery-service",
                correlation_id=str(uuid.uuid4()),
                data=DeliveryStatusChangedEvent.Data(
                    delivery_id=delivery_id,
                    order_id=order_id,
                    old_status=old_status,
                    new_status=new_status,
                    updated_at=datetime.now()
                )
            )
            
            await kafka_producer.publish_event("delivery.events", event, key=order_id)
            logger.info(f"Published delivery.status.changed event for delivery {delivery_id}: {old_status} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Failed to publish delivery.status.changed event: {e}")
    
    async def handle_delivery_created(self, event: Any) -> None:
        """
        Обработка запроса на создание доставки через Kafka
        
        Args:
            event: DeliveryCreatedEvent или словарь с данными
        """
        if hasattr(event, 'data'):
            correlation_id = getattr(event, 'correlation_id', None)
            response_topic = getattr(event, 'response_topic', None)
            data = event.data.model_dump() if hasattr(event.data, 'model_dump') else event.data
        else:
            correlation_id = event.get("correlation_id")
            response_topic = event.get("response_topic")
            data = event.get("data", {})
        
        try:
            delivery_create = DeliveryCreate(
                order_id=uuid.UUID(data.get("order_id")),
                address=data.get("address"),
                delivery_person_id=uuid.UUID(data["delivery_person_id"]) if data.get("delivery_person_id") else None,
                scheduled_time=data.get("scheduled_time"),
                delivery_fee=data.get("delivery_fee", 0.0)
            )
            
            result = await self.delivery_service.create_delivery(delivery_create)
            
            if result:
                await self.publish_delivery_created(result.model_dump())
                
                response = {
                    "correlation_id": correlation_id,
                    "status_code": 201,
                    "data": result.model_dump(mode='json'),
                    "success": True
                }
            else:
                response = {
                    "correlation_id": correlation_id,
                    "status_code": 400,
                    "data": {"detail": "Failed to create delivery"},
                    "success": False
                }
                
            if response_topic:
                await kafka_producer.publish_event(
                    response_topic, 
                    self._create_response_event(response),
                    key=correlation_id
                )
                
        except Exception as e:
            logger.error(f"Error handling delivery created: {e}", exc_info=True)
            if response_topic:
                response = {
                    "correlation_id": correlation_id,
                    "status_code": 500,
                    "data": {"detail": str(e)},
                    "success": False
                }
                await kafka_producer.publish_event(
                    response_topic,
                    self._create_response_event(response),
                    key=correlation_id
                )
    
    async def handle_delivery_updated(self, event: Any) -> None:
        """
        Обработка запроса на обновление доставки через Kafka
        
        Args:
            event: DeliveryUpdatedEvent или словарь с данными
        """
        if hasattr(event, 'data'):
            correlation_id = getattr(event, 'correlation_id', None)
            response_topic = getattr(event, 'response_topic', None)
            data = event.data.model_dump() if hasattr(event.data, 'model_dump') else event.data
        else:
            correlation_id = event.get("correlation_id")
            response_topic = event.get("response_topic")
            data = event.get("data", {})
        
        try:
            delivery_id = data.get("delivery_id")
            new_status = data.get("new_status") or data.get("status")
            
            if not delivery_id or not new_status:
                raise ValueError("delivery_id and new_status are required")
            
            old_delivery = await self.delivery_service.get_delivery_by_id(uuid.UUID(str(delivery_id)))
            old_status = old_delivery.status.value if old_delivery else "unknown"
            
            delivery_update = DeliveryUpdate(status=new_status)
            result = await self.delivery_service.update_delivery(
                uuid.UUID(str(delivery_id)), 
                delivery_update
            )
            
            if result:
                await self.publish_delivery_updated(
                    delivery_id=str(delivery_id),
                    order_id=str(result.order_id),
                    old_status=old_status,
                    new_status=new_status
                )
                
                response = {
                    "correlation_id": correlation_id,
                    "status_code": 200,
                    "data": result.model_dump(mode='json'),
                    "success": True
                }
            else:
                response = {
                    "correlation_id": correlation_id,
                    "status_code": 404,
                    "data": {"detail": "Delivery not found"},
                    "success": False
                }
                
            if response_topic:
                await kafka_producer.publish_event(
                    response_topic,
                    self._create_response_event(response),
                    key=correlation_id
                )
                
        except Exception as e:
            logger.error(f"Error handling delivery updated: {e}", exc_info=True)
            if response_topic:
                response = {
                    "correlation_id": correlation_id,
                    "status_code": 500,
                    "data": {"detail": str(e)},
                    "success": False
                }
                await kafka_producer.publish_event(
                    response_topic,
                    self._create_response_event(response),
                    key=correlation_id
                )
    
    def _create_response_event(self, response_data: Dict[str, Any]) -> Any:
        """Создание события для ответа"""
        from kafka_service.kafka.events import BaseEvent
        
        class ResponseEvent(BaseEvent):
            event_type: EventType = EventType.DELIVERY_RESPONSE
        
        return ResponseEvent(
            source_service="delivery-service",
            correlation_id=response_data.get("correlation_id"),
            data=response_data
        )
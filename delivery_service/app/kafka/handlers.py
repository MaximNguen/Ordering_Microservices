# delivery_service/app/kafka/handlers.py
import json
import logging
import uuid
from typing import Any, Dict

from aiokafka import AIOKafkaProducer
from app.services.delivery import DeliveryService
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate

logger = logging.getLogger(__name__)


class DeliveryKafkaHandlers:
    """Обработчики Kafka событий для доставки"""
    
    def __init__(self, delivery_service: DeliveryService):
        self.delivery_service = delivery_service
        self.producer: AIOKafkaProducer | None = None
        
    async def start_producer(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        await self.producer.start()
        
    async def stop_producer(self):
        if self.producer:
            await self.producer.stop()
            
    async def handle_delivery_created(self, event: Dict[str, Any]):
        correlation_id = event.get("correlation_id")
        response_topic = event.get("response_topic")
        data = event.get("data", {})
        
        try:
            delivery_create = DeliveryCreate(
                order_id=uuid.UUID(data.get("order_id")),
                address=data.get("address"),
                delivery_person_id=uuid.UUID(data.get("delivery_person_id")) if data.get("delivery_person_id") else None,
                scheduled_time=data.get("scheduled_time"),
                delivery_fee=data.get("delivery_fee", 0.0)
            )
            
            result = await self.delivery_service.create_delivery(delivery_create)
            
            if result:
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
                
            if self.producer and response_topic:
                await self.producer.send(response_topic, value=response)
                
        except Exception as e:
            logger.error(f"Error handling delivery created: {e}")
            if self.producer and response_topic:
                await self.producer.send(response_topic, value={
                    "correlation_id": correlation_id,
                    "status_code": 500,
                    "data": {"detail": str(e)},
                    "success": False
                })
import json
import logging
from typing import Any, Dict

from aiokafka import AIOKafkaProducer
from app.services.orders import OrderService
from app.schemas.orders import OrderCreateSchema, OrderUpdateStatusSchema
from app.models.order import OrderStatus

logger = logging.getLogger(__name__)

class OrderKafkaHandler:
    """Обработчики Kafka событий для заказов"""
    
    def __init__(self, order_service: OrderService):
        self.order_service = order_service
        self.producer: AIOKafkaProducer | None = None
        
    async def start_producer(self):
        """Запуск producer для ответов"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        await self.producer.start()
        
    async def stop_producer(self):
        if self.producer:
            await self.producer.stop()
            
    async def handle_order_created(self, event: Dict[str, Any]):
        """Обработка создания заказа через Kafka"""
        correlation_id = event.get("correlation_id")
        response_topic = event.get("response_topic")
        data = event.get("data", {})
        
        try:
            order_create = OrderCreateSchema(
                user_id=data.get("user_id"),
                items=data.get("items", [])
            )
            
            result = await self.order_service.create_order(order_create)
            
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
                    "data": {"detail": "Failed to create order"},
                    "success": False
                }
                
            if self.producer and response_topic:
                await self.producer.send(response_topic, value=response)
                logger.info(f"Sent response for {correlation_id}")
                
        except Exception as e:
            logger.error(f"Error handling order created: {e}")
            if self.producer and response_topic:
                await self.producer.send(response_topic, value={
                    "correlation_id": correlation_id,
                    "status_code": 500,
                    "data": {"detail": str(e)},
                    "success": False
                })
                
    async def handle_order_updated(self, event: Dict[str, Any]):
        """Обработка обновления заказа через Kafka"""
        correlation_id = event.get("correlation_id")
        response_topic = event.get("response_topic")
        data = event.get("data", {})
        
        try:
            order_id = data.get("order_id")
            new_status = data.get("status")
            
            order_update = OrderUpdateStatusSchema(new_status=OrderStatus(new_status))
            result = await self.order_service.update_order_status(order_id, order_update)
            
            if result:
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
                    "data": {"detail": "Order not found"},
                    "success": False
                }
                
            if self.producer and response_topic:
                await self.producer.send(response_topic, value=response)
                logger.info(f"Sent response for {correlation_id}")
                
        except Exception as e:
            logger.error(f"Error handling order updated: {e}")
            if self.producer and response_topic:
                await self.producer.send(response_topic, value={
                    "correlation_id": correlation_id,
                    "status_code": 500,
                    "data": {"detail": str(e)},
                    "success": False
                })
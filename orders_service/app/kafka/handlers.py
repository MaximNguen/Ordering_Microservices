# app/kafka/handlers.py
import json
import logging
import os
import uuid
from typing import Any, Dict
from datetime import datetime

from aiokafka import AIOKafkaProducer
from app.services.orders import OrderService
from app.schemas.orders import OrderCreateSchema, OrderUpdateStatusSchema
from app.models.order import OrderStatus
from kafka_service.kafka.events import (
    OrderCreatedEvent, OrderStatusChangedEvent, 
    OrderItemData, EventType
)

logger = logging.getLogger(__name__)


class OrderKafkaHandler:
    """Обработчики Kafka событий для заказов"""
    
    def __init__(self, order_service: OrderService):
        self.order_service = order_service
        self.producer: AIOKafkaProducer | None = None
        
    async def start_producer(self):
        """Запуск producer для публикации событий"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
        await self.producer.start()
        logger.info("Kafka producer started for order events")
        
    async def stop_producer(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def publish_order_created(self, order_data: Dict[str, Any]):
        """Публикация события о создании заказа"""
        if not self.producer:
            logger.error("Producer not available")
            return
            
        try:
            items = [
                OrderItemData(
                    product_id=item["product_id"],
                    product_name=item["product_name"],
                    quantity=item["quantity"],
                    price_per_unit=item["price_per_unit"]
                )
                for item in order_data.get("items", [])
            ]
            
            event = OrderCreatedEvent(
                source_service="orders-service",
                correlation_id=str(uuid.uuid4()),
                data=OrderCreatedEvent.Data(
                    order_id=str(order_data["order_id"]),
                    user_id=str(order_data["user_id"]),
                    total_amount=order_data["total_amount"],
                    status=order_data["status"],
                    items=items,
                    created_at=datetime.now()
                )
            )
            
            await self.producer.send("order.events", value=event.model_dump(mode='json'))
            logger.info(f"Published order.created event for order {order_data['order_id']}")
            
        except Exception as e:
            logger.error(f"Failed to publish order.created event: {e}")
    
    async def publish_order_status_changed(self, order_id: str, old_status: str, new_status: str, user_id: str):
        """Публикация события об изменении статуса заказа"""
        if not self.producer:
            logger.error("Producer not available")
            return
            
        try:
            event = OrderStatusChangedEvent(
                source_service="orders-service",
                correlation_id=str(uuid.uuid4()),
                data=OrderStatusChangedEvent.Data(
                    order_id=order_id,
                    old_status=old_status,
                    new_status=new_status,
                    updated_at=datetime.utcnow()
                )
            )
            
            await self.producer.send("order.events", value=event.model_dump(mode='json'), key=order_id)
            logger.info(f"Published order.status.changed event for order {order_id}: {old_status} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Failed to publish order.status.changed event: {e}")
    
    async def handle_order_created(self, event: Dict[str, Any]):
        """Обработка запроса на создание заказа через Kafka"""
        correlation_id = event.get("correlation_id")
        response_topic = event.get("response_topic")
        data = event.get("data", {})
        
        try:
            order_create = OrderCreateSchema(
                user_id=uuid.UUID(data.get("user_id")),
                items=data.get("items", [])
            )
            
            result = await self.order_service.create_order(order_create)
            
            if result:
                # Публикуем событие о создании заказа
                await self.publish_order_created(result.model_dump())
                
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
        """Обработка запроса на обновление заказа через Kafka"""
        correlation_id = event.get("correlation_id")
        response_topic = event.get("response_topic")
        data = event.get("data", {})
        
        try:
            order_id = data.get("order_id")
            new_status = data.get("new_status") or data.get("status")
            if not order_id or not new_status:
                raise ValueError("order_id and new_status are required")

            order_id = uuid.UUID(str(order_id))
            order_update = OrderUpdateStatusSchema(new_status=OrderStatus(new_status))
            
            old_order = await self.order_service.get_order_by_id(order_id)
            
            result = await self.order_service.update_order_status(order_id, order_update)
            
            if result:
                await self.publish_order_status_changed(
                    order_id=str(order_id),
                    old_status=old_order.status.value if old_order else "unknown",
                    new_status=new_status,
                    user_id=str(result.user_id)
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


OrderKafkaHandlers = OrderKafkaHandler
import asyncio
import json
import uuid
from typing import Any, Dict, Optional
from datetime import datetime

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import logging

from sqlalchemy import func

logger = logging.getLogger(__name__)


class KafkaRequestResponse:
    """Kafka request-response паттерн для синхронного взаимодействия"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._running = False
        self._response_topic = "gateway.responses"
        
    async def start(self):
        """Запуск producer и consumer для ответов"""
        bootstrap_servers = "localhost:9092"
        
        self.producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8')
        )
        await self.producer.start()
        
        self.consumer = AIOKafkaConsumer(
            self._response_topic,
            bootstrap_servers=bootstrap_servers,
            group_id="gateway-group",
            auto_offset_reset="latest",
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        await self.consumer.start()
        self._running = True
        
        asyncio.create_task(self._listen_responses())
        logger.info("Kafka request-response started")
        
    async def stop(self):
        """Остановка"""
        self._running = False
        if self.producer:
            await self.producer.stop()
        if self.consumer:
            await self.consumer.stop()
            
    async def request(
        self,
        topic: str,
        event_type: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Отправить запрос и дождаться ответа
        
        Args:
            topic: Топик для отправки
            event_type: Тип события
            data: Данные запроса
            timeout: Таймаут ожидания ответа
        
        Returns:
            Ответ от сервиса
        """
        correlation_id = str(uuid.uuid4())
        
        future = asyncio.Future()
        self._pending_requests[correlation_id] = future
        
        try:
            event = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "source_service": "gateway",
                "correlation_id": correlation_id,
                "response_topic": self._response_topic,
                "data": data
            }
            
            await self.producer.send(topic, value=event)
            logger.info(f"Sent request {correlation_id} to {topic}")
            
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response {correlation_id}")
            raise TimeoutError(f"Service {topic} did not respond within {timeout}s")
        finally:
            self._pending_requests.pop(correlation_id, None)
            
    async def _listen_responses(self):
        """Слушаем ответы от сервисов"""
        async for msg in self.consumer:
            try:
                response = msg.value
                correlation_id = response.get("correlation_id")
                
                if correlation_id and correlation_id in self._pending_requests:
                    future = self._pending_requests[correlation_id]
                    if not future.done():
                        future.set_result(response)
                    logger.info(f"Received response for {correlation_id}")
                else:
                    logger.warning(f"Orphan response: {correlation_id}")
                    
            except Exception as e:
                logger.error(f"Error processing response: {e}")
                
kafka_rr = KafkaRequestResponse()
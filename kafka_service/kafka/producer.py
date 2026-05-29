# app/core/kafka/producer.py
import json
import logging
from typing import Any, Dict, Optional

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from kafka.events import BaseEvent
from kafka_service.config import kafka_config

logger = logging.getLogger(__name__)


class KafkaProducerManager:
    """Менеджер Kafka продюсера для отправки событий"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self._started = False

    @property
    def bootstrap_servers(self) -> str:
        return kafka_config.KAFKA_BOOTSTRAP_SERVERS

    async def start(self) -> None:
        """Запуск продюсера"""
        if self._started:
            return

        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                acks=kafka_config.KAFKA_ACKS,
                retries=kafka_config.KAFKA_RETRIES,
                max_in_flight_requests_per_connection=kafka_config.KAFKA_MAX_IN_FLIGHT,
            )
            await self.producer.start()
            self._started = True
            logger.info(f"Kafka producer started. Bootstrap servers: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to start Kafka producer: {e}")
            raise

    async def stop(self) -> None:
        """Остановка продюсера"""
        if self.producer and self._started:
            await self.producer.stop()
            self._started = False
            logger.info("Kafka producer stopped")

    async def send_event(self, topic: str, event: BaseEvent, key: Optional[str] = None) -> None:
        """
        Отправка события в Kafka
        
        Args:
            topic: Название топика
            event: Событие (наследник BaseEvent)
            key: Ключ для партиционирования (обычно ID сущности)
        """
        if not self._started or not self.producer:
            logger.error("Producer not started, cannot send event")
            raise RuntimeError("Kafka producer not started")

        try:
            event_dict = event.model_dump(mode='json')
            key_bytes = key.encode('utf-8') if key else None
            
            await self.producer.send(topic, value=event_dict, key=key_bytes)
            logger.debug(f"Event sent to {topic}: {event.event_type} (id={event.event_id})")
        except KafkaError as e:
            logger.error(f"Kafka error sending event to {topic}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending event to {topic}: {e}")
            raise

    async def send_event_and_wait(self, topic: str, event: BaseEvent, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Отправка события с ожиданием подтверждения
        Возвращает метаданные о发送нном сообщении
        """
        if not self._started or not self.producer:
            raise RuntimeError("Kafka producer not started")

        try:
            event_dict = event.model_dump(mode='json')
            key_bytes = key.encode('utf-8') if key else None
            
            metadata = await self.producer.send(topic, value=event_dict, key=key_bytes)
            result = await metadata
            logger.info(f"Event confirmed: topic={topic}, partition={result.partition}, offset={result.offset}")
            return {
                "topic": result.topic,
                "partition": result.partition,
                "offset": result.offset,
            }
        except KafkaError as e:
            logger.error(f"Kafka error: {e}")
            raise


kafka_producer = KafkaProducerManager()
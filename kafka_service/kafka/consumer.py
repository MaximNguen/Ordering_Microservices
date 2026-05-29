# app/core/kafka/consumer.py
import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional, Awaitable

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from config import kafka_config
from kafka.events import BaseEvent, EventType

logger = logging.getLogger(__name__)


class KafkaConsumerManager:
    """Менеджер Kafka консьюмера для обработки событий"""
    
    def __init__(self):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._handlers: Dict[EventType, Callable[[BaseEvent], Awaitable[None]]] = {}

    def register_handler(self, event_type: EventType, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        """Регистрация обработчика для определенного типа событий"""
        self._handlers[event_type] = handler
        logger.info(f"Registered handler for event type: {event_type}")

    async def start(self, topics: list[str], group_id: Optional[str] = None) -> None:
        """Запуск консьюмера"""
        if self._running:
            return

        try:
            self.consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id or kafka_config.KAFKA_GROUP_ID,
                auto_offset_reset=kafka_config.KAFKA_AUTO_OFFSET_RESET,
                enable_auto_commit=kafka_config.KAFKA_ENABLE_AUTO_COMMIT,
                max_poll_records=kafka_config.KAFKA_MAX_POLL_RECORDS,
                session_timeout_ms=kafka_config.KAFKA_SESSION_TIMEOUT_MS,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')) if v else None,
            )
            await self.consumer.start()
            self._running = True
            logger.info(f"Kafka consumer started. Topics: {topics}, Group: {group_id}")
            
            self._tasks.append(asyncio.create_task(self._consume_loop()))
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {e}")
            raise

    async def stop(self) -> None:
        """Остановка консьюмера"""
        self._running = False
        
        # Отмена всех задач
        for task in self._tasks:
            task.cancel()
        
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped")

    async def _consume_loop(self) -> None:
        """Основной цикл потребления сообщений"""
        try:
            async for msg in self.consumer:
                try:
                    await self._process_message(msg)
                    if not kafka_config.KAFKA_ENABLE_AUTO_COMMIT:
                        await self.consumer.commit()
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Отправка в DLQ при ошибке
                    await self._send_to_dlq(msg, str(e))
        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled")
        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
        finally:
            self._running = False

    async def _process_message(self, msg) -> None:
        """Обработка одного сообщения"""
        if not msg.value:
            logger.warning("Empty message received")
            return

        event_data = msg.value
        event_type_str = event_data.get("event_type")
        
        if not event_type_str:
            logger.warning(f"Message missing event_type: {event_data}")
            return

        try:
            event_type = EventType(event_type_str)
            handler = self._handlers.get(event_type)
            
            if handler:
                # Создание события (нужно будет доработать в зависимости от типа)
                event = BaseEvent(**event_data)
                await handler(event)
                logger.debug(f"Processed event: {event_type}")
            else:
                logger.warning(f"No handler registered for event type: {event_type}")
        except ValueError as e:
            logger.error(f"Invalid event type: {event_type_str}, error: {e}")

    async def _send_to_dlq(self, msg, error: str) -> None:
        """Отправка сообщения в Dead Letter Queue"""
        try:
            dlq_producer = AIOKafkaProducer(
                bootstrap_servers=kafka_config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            )
            await dlq_producer.start()
            
            dlq_message = {
                "original_message": msg.value,
                "error": error,
                "timestamp": msg.timestamp,
                "topic": msg.topic,
                "partition": msg.partition,
                "offset": msg.offset,
            }
            await dlq_producer.send(kafka_config.TOPIC_DLQ, value=dlq_message)
            await dlq_producer.stop()
            logger.warning(f"Message sent to DLQ: {error}")
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")


kafka_consumer = KafkaConsumerManager()
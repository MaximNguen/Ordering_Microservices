from contextlib import asynccontextmanager
import logging
import os
import json
import asyncio
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.database import create_db_and_tables
from app.api.routers import delivery
from app.kafka.handlers import DeliveryKafkaHandlers
from app.repositories.delivery import DeliveryRepository
from app.core.database import AsyncSessionLocal
from app.services.delivery import DeliveryService

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

from app.core.database import create_db_and_tables
from app.api.routers import delivery


def _find_file_handler(logger: logging.Logger, log_file: Path) -> RotatingFileHandler | None:
    target = log_file.resolve()
    for handler in logger.handlers:
        if isinstance(handler, RotatingFileHandler):
            try:
                if Path(handler.baseFilename).resolve() == target:
                    return handler
            except OSError:
                continue
    return None


def _configure_logging() -> None:
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    startup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"delivery_service_{startup_time}.log" 

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "1000000"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "3"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    file_handler = _find_file_handler(root_logger, log_file)
    if file_handler is None:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger.addHandler(file_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.setLevel(log_level)
        if not uvicorn_logger.propagate and _find_file_handler(uvicorn_logger, log_file) is None:
            uvicorn_logger.addHandler(file_handler)


_configure_logging()
logger = logging.getLogger(__name__)

kafka_handlers: Optional[DeliveryKafkaHandlers] = None
kafka_consumer: Optional[AIOKafkaConsumer] = None
kafka_producer: Optional[AIOKafkaProducer] = None
consume_task: Optional[asyncio.Task] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # await create_db_and_tables()
    async with AsyncSessionLocal() as session:
        delivery_repo = DeliveryRepository(session)
        delivery_service = DeliveryService(delivery_repo)
        
        kafka_handlers = DeliveryKafkaHandlers(delivery_service)
        await kafka_handlers.start_producer()
        
        bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        
        kafka_consumer = AIOKafkaConsumer(
            "delivery.events",
            bootstrap_servers=bootstrap_servers,
            group_id="delivery-service-group",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode('utf-8')) if v else None
        )
        await kafka_consumer.start()
        logger.info(f"Delivery Kafka consumer started on topic 'delivery.events'")
        
        async def consume_loop():
            try:
                async for msg in kafka_consumer:
                    try:
                        event = msg.value
                        if not event:
                            continue
                            
                        event_type = event.get("event_type")
                        logger.info(f"Received event: {event_type}")
                        
                        if event_type == "delivery.created":
                            await kafka_handlers.handle_delivery_created(event)
                        elif event_type == "delivery.updated":
                            await kafka_handlers.handle_delivery_updated(event)
                        else:
                            logger.warning(f"Unknown event type: {event_type}")
                            
                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)
                        
            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled")
            except Exception as e:
                logger.error(f"Consumer loop error: {e}", exc_info=True)
            finally:
                logger.info("Consumer loop finished")
        
    consume_task = asyncio.create_task(consume_loop())
    
    yield
        
    if consume_task:
        consume_task.cancel()
        try:
            await consume_task
        except asyncio.CancelledError:
            pass
                    
    if kafka_consumer:
        await kafka_consumer.stop()
        logger.info("Kafka consumer stopped")
                
    if kafka_handlers:
        await kafka_handlers.stop_producer()
        logger.info("Kafka producer stopped")
    logger.info("Заканчиваем работу.")
    
app = FastAPI(
    title="Сервис доставки",
    lifespan=lifespan
)

app.include_router(delivery.router)

@app.get("/")
async def root():
    return {"message": "Сервис доставки работает!"}
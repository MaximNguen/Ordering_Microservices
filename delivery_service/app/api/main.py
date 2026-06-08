from contextlib import asynccontextmanager
import logging
import os
import asyncio
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from app.core.database import create_db_and_tables
from app.api.routers.delivery import require_service_auth
from app.kafka.handlers import DeliveryKafkaHandlers
from app.repositories.delivery import DeliveryRepository
from app.core.database import AsyncSessionLocal
from app.services.delivery import DeliveryService
from app.core.cache_listener import CacheInvalidationListener
from cache_settings.redis_client import init_redis, close_redis
from kafka_service.kafka.consumer import kafka_consumer
from kafka_service.kafka.producer import kafka_producer
from kafka_service.kafka.events import EventType
from app.api.routers import delivery

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()


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
consume_task: Optional[asyncio.Task] = None
cache_listener = CacheInvalidationListener()

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

delivery_created_counter = Counter(
    'delivery_created_total', 
    'Total number of deliveries created',
    ['status']
)

delivery_updated_counter = Counter(
    'delivery_updated_total',
    'Total number of deliveries updated',
    ['field']
)

delivery_delete_counter = Counter(
    'delivery_deleted_total',
    'Total number of deliveries deleted'
)

kafka_messages_received = Counter(
    'kafka_messages_received_total',
    'Total Kafka messages received',
    ['event_type', 'topic']
)

kafka_processing_time = Histogram(
    'kafka_message_processing_seconds',
    'Time spent processing Kafka messages',
    ['event_type'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

active_deliveries_gauge = Gauge(
    'active_deliveries_count',
    'Current number of active deliveries'
)

db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    await init_redis()
    cache_listener.start()
    await kafka_producer.start()
    logger.info("Kafka producer started")
    async with AsyncSessionLocal() as session:
        delivery_repo = DeliveryRepository(session)
        delivery_service = DeliveryService(delivery_repo)
        
        kafka_handlers = DeliveryKafkaHandlers(delivery_service)
        kafka_consumer.register_handler(EventType.DELIVERY_CREATED, kafka_handlers.handle_delivery_created)
        kafka_consumer.register_handler(EventType.DELIVERY_UPDATED, kafka_handlers.handle_delivery_updated)

        await kafka_consumer.start(
            topics=["delivery.events", "delivery.requests"],
            group_id="delivery-service-group"
        )
        logger.info("Kafka consumer started for delivery service")
        
        app.state.kafka_handlers = kafka_handlers
        app.state.delivery_service = delivery_service
        
        yield

        await kafka_consumer.stop()
        await kafka_producer.stop()
        logger.info("Kafka stopped")
    await close_redis()
    await cache_listener.stop()
    logger.info("Заканчиваем работу.")
    
app = FastAPI(
    title="Сервис доставки",
    lifespan=lifespan
)

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)
instrumentator.add().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
app.include_router(delivery.router, dependencies=[Depends(require_service_auth)])

@app.get("/")
async def root():
    return {"message": "Сервис доставки работает!"}
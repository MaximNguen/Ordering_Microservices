# orders_service/main.py (исправленный)
import asyncio
from contextlib import asynccontextmanager
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

from app.core.database import create_db_and_tables
from app.api.routers import orders
from app.core.database import AsyncSessionLocal
from app.repositories.orders import OrderRepository
from app.services.orders import OrderService
from app.kafka.handlers import OrderKafkaHandlers
from app.core.cache_listener import CacheInvalidationListener
from cache_settings.redis_client import init_redis, close_redis
from kafka_service.kafka.consumer import kafka_consumer
from kafka_service.kafka.producer import kafka_producer
from kafka_service.kafka.events import EventType
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


def _configure_logging() -> None:
    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    startup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"orders_service_{startup_time}.log"

    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    max_bytes = int(os.getenv("LOG_MAX_BYTES", "1000000"))
    backup_count = int(os.getenv("LOG_BACKUP_COUNT", "3"))

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

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
        if not uvicorn_logger.propagate:
            uvicorn_logger.addHandler(file_handler)


_configure_logging()
logger = logging.getLogger(__name__)

cache_listener = CacheInvalidationListener()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Orders Service...")
    
    await init_redis()
    cache_listener.start()
    
    await kafka_producer.start()
    logger.info("Kafka producer started")
    
    async with AsyncSessionLocal() as session:
        order_repo = OrderRepository(db=session)
        order_service = OrderService(order_repo=order_repo)
        
        kafka_handlers = OrderKafkaHandlers(order_service)
        
        kafka_consumer.register_handler(EventType.ORDER_CREATED, kafka_handlers.handle_order_created)
        kafka_consumer.register_handler(EventType.ORDER_STATUS_CHANGED, kafka_handlers.handle_order_updated)
        
        await kafka_consumer.start(
            topics=["order.events", "order.requests"],
            group_id="orders-service-group"
        )
        logger.info("Kafka consumer started for orders service")
        
        app.state.kafka_handlers = kafka_handlers
        app.state.order_service = order_service
        
        yield
        
        await kafka_consumer.stop()
        await kafka_producer.stop()
        logger.info("Kafka stopped")
    
    await cache_listener.stop()
    await close_redis()
    logger.info("Orders Service shutdown complete")


app = FastAPI(title="Orders Service", lifespan=lifespan)

app.include_router(orders.router)

@app.get("/")
@limiter.limit("100/minute")
async def root():
    return {"message": "Orders Service is running"}
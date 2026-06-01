import asyncio
from contextlib import asynccontextmanager
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI
from aiokafka import AIOKafkaConsumer
import json

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
    log_file = log_dir / f"orders_service_{startup_time}.log"

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

kafka_handlers = None
kafka_consumer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # await create_db_and_tables()
    logger.info("Starting database initialization.")
    async with AsyncSessionLocal() as session:
        order_repo = OrderRepository(db=session)
        order_service = OrderService(order_repo=order_repo)
        kafka_handlers = OrderKafkaHandlers(order_service)
        await kafka_handlers.start_producer()

        kafka_consumer = AIOKafkaConsumer(
            "order.events",
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            group_id="orders-service-group",
            auto_offset_reset="earliest",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
        )
        await kafka_consumer.start()
        logger.info("Kafka consumer started for orders service.")

        async def consume_loop():
            async for msg in kafka_consumer:
                try:
                    event = msg.value
                    event_type = event.get("event_type")

                    if event_type == "order.created":
                        await kafka_handlers.handle_order_created(event)
                    elif event_type == "order.status.changed":
                        await kafka_handlers.handle_order_updated(event)
                    else:
                        logger.warning(f"Unknown event type: {event_type}")

                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        app.state.consume_task = asyncio.create_task(consume_loop())

        yield

        if hasattr(app.state, "consume_task"):
            app.state.consume_task.cancel()
            try:
                await app.state.consume_task
            except asyncio.CancelledError:
                pass
        await kafka_consumer.stop()
        await kafka_handlers.stop_producer()
    logger.info("Shutting down.")


app = FastAPI(title="Orders service", lifespan=lifespan)

app.include_router(orders.router)

@app.get("/")
async def root():
    return {"message": "Orders service is running"}

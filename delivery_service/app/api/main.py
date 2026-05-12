from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

from app.core.database import create_db_and_tables
from app.api.routers import delivery

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # await create_db_and_tables()
    logger.info("Запускаем создание БД.")
    yield
    logger.info("Заканчиваем работу.")
    
app = FastAPI(
    title="Сервис доставки",
    lifespan=lifespan
)

app.include_router(delivery.router)

@app.get("/")
async def root():
    return {"message": "Сервис доставки работает!"}
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import logging

from app.core.database import create_db_and_tables
from app.core.exceptions import AuthError
from app.api.routers import users

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # await create_db_and_tables()
    logger.info("Запускаем создание БД.")
    yield
    logger.info("Заканчиваем работу.")
    
app = FastAPI(
    title="Сервис пользователей/авторизации",
    lifespan=lifespan
)

app.include_router(users.router)

@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError):
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.detail},
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.get("/")
async def root():
    return {"message": "Сервис доставки работает!"}
import os
import logging

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/users_db")

engine = create_async_engine(DATABASE_URL, echo=True)

class Base(DeclarativeBase):
    pass

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def create_db_and_tables():
    async with engine.begin() as conn:
        logger.info("Создание базы данных и таблиц...")
        await conn.run_sync(Base.metadata.create_all)
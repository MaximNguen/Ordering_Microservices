import logging

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.repositories.products import ProductRepository
from app.services.products import ProductService

logger = logging.getLogger(__name__)


async def get_async_db():
    async with AsyncSessionLocal() as db:
        logger.info("Fetching async DB session.")
        yield db
        logger.info("Async DB session closed.")


def get_product_repository(db: AsyncSession = Depends(get_async_db)) -> ProductRepository:
    logger.info("Fetching product repository.")
    return ProductRepository(db=db)


def get_product_service(
    product_repo: ProductRepository = Depends(get_product_repository),
) -> ProductService:
    logger.info("Fetching product service.")
    return ProductService(product_repo=product_repo)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging
import uuid

from app.models.product import Product

class ProductRepository:
    """Класс-репозиторий для управления данными о продуктах, обеспечивающий взаимодействие с базой данных."""
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    async def get_product_by_id(self, product_id: uuid.UUID) -> Product | None:
        self.logger.info(f"Получение продукта по ID: {product_id}")
        try:
            result = await self.db.scalar(select(Product).where(Product.product_id == product_id))
        except Exception as e:
            self.logger.error(f"Ошибка при получении продукта по ID: {product_id}, ошибка: {e}")
            result = None
        return result   

    async def get_all_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        self.logger.info("Получение всех продуктов")
        try:
            result = await self.db.scalars(select(Product).offset(skip).limit(limit))
        except Exception as e:
            self.logger.error(f"Ошибка при получении всех продуктов, ошибка: {e}")
            result = []
        return list(result)
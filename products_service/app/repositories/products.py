import logging
import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepository:
    """Repository for product persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)

    async def create_product(self, product: Product) -> Product | None:
        self.logger.info("Creating product: %s", product.name)
        try:
            self.db.add(product)
            await self.db.commit()
            await self.db.refresh(product)
            return product
        except Exception as exc:
            self.logger.error("Failed to create product: %s", exc)
            await self.db.rollback()
            return None

    async def get_product_by_id(self, product_id: uuid.UUID) -> Product | None:
        self.logger.info("Fetching product by id: %s", product_id)
        try:
            return await self.db.scalar(select(Product).where(Product.product_id == product_id))
        except Exception as exc:
            self.logger.error("Failed to fetch product by id %s: %s", product_id, exc)
            return None

    async def get_all_products(self, skip: int = 0, limit: int = 100) -> List[Product]:
        self.logger.info("Fetching all products.")
        try:
            result = await self.db.scalars(select(Product).offset(skip).limit(limit))
            return list(result)
        except Exception as exc:
            self.logger.error("Failed to fetch products: %s", exc)
            return []

    async def update_product(
        self,
        product_id: uuid.UUID,
        *,
        name: str | None,
        description: str | None,
        price: float | None,
    ) -> Product | None:
        self.logger.info("Updating product: %s", product_id)
        try:
            product = await self.db.scalar(select(Product).where(Product.product_id == product_id))
            if not product:
                return None
            if name is not None:
                product.name = name
            if description is not None:
                product.description = description
            if price is not None:
                product.price = price
            await self.db.commit()
            await self.db.refresh(product)
            return product
        except Exception as exc:
            self.logger.error("Failed to update product %s: %s", product_id, exc)
            await self.db.rollback()
            return None

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        self.logger.info("Deleting product: %s", product_id)
        try:
            product = await self.db.scalar(select(Product).where(Product.product_id == product_id))
            if not product:
                return False
            await self.db.delete(product)
            await self.db.commit()
            return True
        except Exception as exc:
            self.logger.error("Failed to delete product %s: %s", product_id, exc)
            await self.db.rollback()
            return False

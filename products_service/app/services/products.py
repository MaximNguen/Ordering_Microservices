import logging
import uuid

from app.models.product import Product
from app.repositories.products import ProductRepository
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate


class ProductService:
    """Service layer for product business logic."""

    def __init__(self, product_repo: ProductRepository):
        self.product_repo = product_repo
        self.logger = logging.getLogger(__name__)

    async def create_product(self, product_create: ProductCreate) -> ProductResponse | None:
        self.logger.info("Creating product with name: %s", product_create.name)
        product = Product(
            name=product_create.name,
            description=product_create.description,
            price=product_create.price,
        )
        db_product = await self.product_repo.create_product(product)
        if not db_product:
            return None
        return ProductResponse.model_validate(db_product)

    async def get_product_by_id(self, product_id: uuid.UUID) -> ProductResponse | None:
        self.logger.info("Fetching product by id: %s", product_id)
        db_product = await self.product_repo.get_product_by_id(product_id)
        if not db_product:
            return None
        return ProductResponse.model_validate(db_product)

    async def get_all_products(self, skip: int = 0, limit: int = 100) -> list[ProductResponse]:
        self.logger.info("Fetching products list.")
        db_products = await self.product_repo.get_all_products(skip=skip, limit=limit)
        return [ProductResponse.model_validate(product) for product in db_products]

    async def update_product(
        self,
        product_id: uuid.UUID,
        product_update: ProductUpdate,
    ) -> ProductResponse | None:
        self.logger.info("Updating product by id: %s", product_id)
        db_product = await self.product_repo.update_product(
            product_id,
            name=product_update.name,
            description=product_update.description,
            price=product_update.price,
        )
        if not db_product:
            return None
        return ProductResponse.model_validate(db_product)

    async def delete_product(self, product_id: uuid.UUID) -> bool:
        self.logger.info("Deleting product by id: %s", product_id)
        return await self.product_repo.delete_product(product_id)

import uuid
import logging

from app.repositories.delivery import DeliveryRepository
from app.schemas.delivery import DeliveryCreate, DeliveryUpdate, DeliveryResponse

class DeliveryService:
    """Класс-сервис для управления логикой доставки, обеспечивающий взаимодействие между репозиторием и API."""
    def __init__(self, delivery_repo: DeliveryRepository):
        self.delivery_repo = delivery_repo
        self.logger = logging.getLogger(__name__)
        
    async def create_delivery(self, delivery_create: DeliveryCreate) -> DeliveryResponse:
        self.logger.info(f"Создание доставки для заказа {delivery_create.order_id}")
        db_delivery = await self.delivery_repo.create_delivery(
            order_id=delivery_create.order_id,
            address=delivery_create.address,
            delivery_person_id=delivery_create.delivery_person_id,
            scheduled_time=delivery_create.scheduled_time,
            delivery_fee=delivery_create.delivery_fee,
        )
        return DeliveryResponse.model_validate(db_delivery)
    
    async def get_delivery_by_id(self, delivery_id: uuid.UUID) -> DeliveryResponse | None:
        self.logger.info(f"Получение доставки по ID: {delivery_id}")
        db_delivery = await self.delivery_repo.get_by_delivery_id(delivery_id)
        if not db_delivery:
            return None
        return DeliveryResponse.model_validate(db_delivery)
    
    async def get_all_deliveries(self, skip: int = 0, limit: int = 100) -> list[DeliveryResponse]:
        db_deliveries = await self.delivery_repo.get_all(skip=skip, limit=limit)
        return [DeliveryResponse.model_validate(delivery) for delivery in db_deliveries]
    
    async def update_delivery(self, delivery_id: uuid.UUID, delivery_update: DeliveryUpdate) -> DeliveryResponse | None:
        self.logger.info(f"Обновление доставки с ID: {delivery_id}")
        try:
            db_delivery = await self.delivery_repo.update_delivery(
                delivery_id,
                status=delivery_update.status,
            )
        except ValueError:
            return None

        return DeliveryResponse.model_validate(db_delivery)
    
    async def delete_delivery(self, delivery_id: uuid.UUID) -> bool:
        self.logger.info(f"Удаление доставки с ID: {delivery_id}")
        try:
            await self.delivery_repo.delete_delivery(delivery_id)
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при удалении доставки с ID: {delivery_id}, ошибка: {e}")
            return False
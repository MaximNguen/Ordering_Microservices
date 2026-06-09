from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone
from typing import List
import logging
import uuid

from app.models.delivery import Delivery, DeliveryStatus

class DeliveryRepository:
    """Класс-репозиторий для управления данными о доставках, обеспечивающий взаимодействие с базой данных."""
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    async def get_by_delivery_id(self, delivery_id: uuid.UUID) -> Delivery | None:
        self.logger.info(f"Getting delivery by ID: {delivery_id}")
        try:
            result = await self.db.scalar(select(Delivery).where(Delivery.delivery_id == delivery_id))
        except Exception as e:
            self.logger.error(f"Error occurred while fetching delivery by ID: {delivery_id}, error: {e}")
            result = None
        return result
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Delivery]:
        self.logger.info("Getting all deliveries with skip=%d and limit=%d", skip, limit)
        try:
            result = await self.db.scalars(select(Delivery).offset(skip).limit(limit))
        except Exception as e:
            self.logger.error(f"Error occurred while fetching all deliveries, error: {e}")
            result = []
        return list(result)
    
    async def create_delivery(
        self,
        *,
        order_id: uuid.UUID,
        address: str,
        delivery_person_id: uuid.UUID | None = None,
        scheduled_time: datetime | None = None,
        delivery_fee: float = 0.0,
        status: DeliveryStatus | None = None,
    ) -> Delivery:
        self.logger.info(
            "Creating new delivery (order_id=%s, delivery_person_id=%s)",
            order_id,
            delivery_person_id,
        )

        if scheduled_time and scheduled_time.tzinfo is not None and scheduled_time.tzinfo.utcoffset(scheduled_time) is not None:
            scheduled_time = scheduled_time.astimezone(timezone.utc).replace(tzinfo=None)

        delivery = Delivery(
            order_id=order_id,
            address=address,
            delivery_person_id=delivery_person_id,
            scheduled_time=scheduled_time,
            delivery_fee=delivery_fee,
        )

        if status is not None:
            delivery.status = status

        try:
            self.db.add(delivery)
            await self.db.commit()
            await self.db.refresh(delivery)
        except Exception as e:
            self.logger.error(f"Error occurred while creating delivery: {delivery}, error: {e}")
            await self.db.rollback()
            raise
        return delivery
    
    async def update_delivery(
        self,
        delivery_id: uuid.UUID,
        *,
        status: DeliveryStatus | None = None,
    ) -> Delivery:
        self.logger.info("Updating delivery (delivery_id=%s)", delivery_id)
        delivery = await self.get_by_delivery_id(delivery_id)
        if not delivery:
            raise ValueError(f"Delivery with ID: {delivery_id} not found")

        if status is not None:
            delivery.status = status

        try:
            await self.db.commit()
            await self.db.refresh(delivery)
        except Exception as e:
            self.logger.error(f"Error occurred while updating delivery: {delivery}, error: {e}")
            await self.db.rollback()
            raise
        return delivery
    
    # app/repositories/delivery.py
    async def delete_delivery(self, delivery_id: uuid.UUID) -> None:
        self.logger.info(f"Deleting delivery (delivery_id={str(delivery_id)})")
        try:
            delivery = await self.db.get(Delivery, delivery_id)
            
            if not delivery:
                raise ValueError(f"Delivery with ID: {delivery_id} not found for deletion.")
            delivery.status = DeliveryStatus.DELETED
            await self.db.commit()
            await self.db.refresh(delivery)
            self.logger.info(f"Delivery {delivery_id} successfully deleted (status changed to DELETED)")
        except Exception as e:
            self.logger.error(f"Error occurred while deleting delivery with ID: {delivery_id}, error: {e}")
            await self.db.rollback()
            raise
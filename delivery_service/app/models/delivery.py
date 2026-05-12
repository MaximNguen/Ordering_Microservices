from sqlalchemy import String, Float, DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class DeliveryStatus(enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DELETED = "deleted"

class Delivery(Base):
    """Класс модели доставки, представляющий таблицу 'deliveries' в базе данных."""
    __tablename__ = "deliveries"

    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    delivery_person_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    status: Mapped[DeliveryStatus] = mapped_column(Enum(DeliveryStatus), default=DeliveryStatus.PENDING)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    actual_delivery_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    delivery_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BookingStatus(str, Enum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id", ondelete="RESTRICT"), nullable=False, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=BookingStatus.CONFIRMED.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    slot = relationship("TimeSlot", back_populates="booking")
    client = relationship("User", back_populates="bookings")

    def cancel(self) -> None:
        self.status = BookingStatus.CANCELLED.value
        self.cancelled_at = datetime.now(UTC)

from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import Booking, BookingStatus, SpecialistProfile, TimeSlot, User, UserRole
from app.tasks.expirations import expire_started_slots
from app.tasks.reminders import count_upcoming_bookings_for_reminder


def _build_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return TestSession()


def _seed_specialist_and_client(db: Session) -> tuple[User, User, SpecialistProfile]:
    specialist = User(email="task-spec@example.com", hashed_password="x", role=UserRole.SPECIALIST.value)
    client = User(email="task-client@example.com", hashed_password="x", role=UserRole.CLIENT.value)
    db.add_all([specialist, client])
    db.flush()
    profile = SpecialistProfile(user_id=specialist.id, display_name="Spec", description=None)
    db.add(profile)
    db.flush()
    return specialist, client, profile


def test_expire_started_slots_marks_booking_as_expired():
    db = _build_session()
    _, client, profile = _seed_specialist_and_client(db)
    now = datetime.now(UTC)
    slot = TimeSlot(
        specialist_id=profile.id,
        start_at=now - timedelta(hours=2),
        end_at=now - timedelta(hours=1),
        is_booked=True,
    )
    db.add(slot)
    db.flush()
    booking = Booking(slot_id=slot.id, client_id=client.id, status=BookingStatus.CONFIRMED.value)
    db.add(booking)
    db.commit()

    expired = expire_started_slots(db=db, now=now)
    updated_booking = db.get(Booking, booking.id)
    updated_slot = db.get(TimeSlot, slot.id)

    assert expired == 1
    assert updated_booking is not None
    assert updated_booking.status == BookingStatus.EXPIRED.value
    assert updated_booking.cancelled_at is not None
    assert updated_slot is not None
    assert updated_slot.is_booked is False
    db.close()


def test_count_upcoming_bookings_for_reminder_counts_only_near_window():
    db = _build_session()
    _, client, profile = _seed_specialist_and_client(db)
    now = datetime.now(UTC)

    near_slot = TimeSlot(
        specialist_id=profile.id,
        start_at=now + timedelta(minutes=30),
        end_at=now + timedelta(minutes=90),
        is_booked=True,
    )
    far_slot = TimeSlot(
        specialist_id=profile.id,
        start_at=now + timedelta(hours=5),
        end_at=now + timedelta(hours=6),
        is_booked=True,
    )
    db.add_all([near_slot, far_slot])
    db.flush()
    db.add_all(
        [
            Booking(slot_id=near_slot.id, client_id=client.id, status=BookingStatus.CONFIRMED.value),
            Booking(slot_id=far_slot.id, client_id=client.id, status=BookingStatus.CONFIRMED.value),
        ]
    )
    db.commit()

    count = count_upcoming_bookings_for_reminder(db=db, now=now)
    assert count == 1
    db.close()

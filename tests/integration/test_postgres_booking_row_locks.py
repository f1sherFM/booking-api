import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Booking, BookingStatus, SpecialistProfile, TimeSlot, User, UserRole
from app.services.booking_service import LOCK_CONFLICT_DETAIL, create_booking_for_slot

TEST_POSTGRES_DATABASE_URL = os.getenv("TEST_POSTGRES_DATABASE_URL")


@pytest.fixture(scope="module")
def postgres_session_factory():
    if not TEST_POSTGRES_DATABASE_URL:
        pytest.skip("TEST_POSTGRES_DATABASE_URL is not set")

    engine = create_engine(TEST_POSTGRES_DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.mark.postgres
def test_postgres_booking_lock_conflict_then_success(postgres_session_factory):
    seed_session = postgres_session_factory()
    specialist_user = User(
        email="pg-lock-spec@example.com",
        hashed_password="x",
        role=UserRole.SPECIALIST.value,
    )
    client_user = User(
        email="pg-lock-client@example.com",
        hashed_password="x",
        role=UserRole.CLIENT.value,
    )
    seed_session.add_all([specialist_user, client_user])
    seed_session.flush()

    profile = SpecialistProfile(user_id=specialist_user.id, display_name="PG Specialist", description=None)
    seed_session.add(profile)
    seed_session.flush()

    slot = TimeSlot(
        specialist_id=profile.id,
        start_at=datetime.now(UTC) + timedelta(hours=1),
        end_at=datetime.now(UTC) + timedelta(hours=2),
        is_booked=False,
    )
    seed_session.add(slot)
    seed_session.commit()
    slot_id = slot.id
    client_id = client_user.id
    seed_session.close()

    lock_holder = postgres_session_factory()
    try:
        locked_slot = lock_holder.scalar(
            select(TimeSlot).where(TimeSlot.id == slot_id).with_for_update()
        )
        assert locked_slot is not None

        contender = postgres_session_factory()
        try:
            with pytest.raises(HTTPException) as exc_info:
                create_booking_for_slot(db=contender, slot_id=slot_id, client_id=client_id)
            assert exc_info.value.status_code == 409
            assert exc_info.value.detail == LOCK_CONFLICT_DETAIL
        finally:
            contender.close()
    finally:
        lock_holder.rollback()
        lock_holder.close()

    success_session = postgres_session_factory()
    booking = create_booking_for_slot(db=success_session, slot_id=slot_id, client_id=client_id)
    success_session.close()

    assert booking.status == BookingStatus.CONFIRMED.value

    check_session = postgres_session_factory()
    total_bookings = check_session.query(Booking).count()
    final_slot = check_session.scalar(select(TimeSlot).where(TimeSlot.id == slot_id))
    check_session.close()

    assert total_bookings == 1
    assert final_slot is not None
    assert final_slot.is_booked is True

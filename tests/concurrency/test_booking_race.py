from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Booking, SpecialistProfile, TimeSlot, User, UserRole
from app.services.booking_service import create_booking_for_slot


@pytest.mark.concurrent
def test_two_parallel_booking_attempts_only_one_succeeds(tmp_path):
    db_file = tmp_path / "race.db"
    engine = create_engine(f"sqlite+pysqlite:///{db_file}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    seed_session = SessionLocal()
    specialist_user = User(email="race-spec@example.com", hashed_password="x", role=UserRole.SPECIALIST.value)
    client_user = User(email="race-client@example.com", hashed_password="x", role=UserRole.CLIENT.value)
    seed_session.add_all([specialist_user, client_user])
    seed_session.flush()
    profile = SpecialistProfile(user_id=specialist_user.id, display_name="Race Specialist", description=None)
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

    def attempt() -> str:
        session = SessionLocal()
        try:
            create_booking_for_slot(db=session, slot_id=slot_id, client_id=client_id)
            return "created"
        except HTTPException as exc:
            if exc.status_code == 409:
                return "conflict"
            raise
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: attempt(), range(2)))

    assert sorted(results) == ["conflict", "created"]

    check = SessionLocal()
    total_bookings = check.query(Booking).count()
    final_slot = check.query(TimeSlot).filter(TimeSlot.id == slot_id).one()
    check.close()

    assert total_bookings == 1
    assert final_slot.is_booked is True

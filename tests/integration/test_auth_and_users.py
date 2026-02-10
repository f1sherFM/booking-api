def test_register_success(client):
    payload = {
        "email": "user1@example.com",
        "password": "StrongPass123",
        "role": "client",
    }

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == payload["role"]
    assert data["is_active"] is True
    assert "id" in data


def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "StrongPass123",
        "role": "client",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "User with this email already exists"


def test_login_success(client):
    payload = {
        "email": "login@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=payload)

    response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 20


def test_users_me_with_token(client):
    payload = {
        "email": "me@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=payload)
    login = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    token = login.json()["access_token"]

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == payload["role"]


def test_users_me_without_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_specialist_can_create_service_and_read_list(client):
    specialist_payload = {
        "email": "specialist@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    token = login.json()["access_token"]

    create_response = client.post(
        "/specialists/me/services",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Haircut",
            "description": "Classic haircut service",
            "duration_minutes": 60,
            "price": "25.00",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    specialist_id = created["specialist_id"]
    assert created["title"] == "Haircut"

    list_response = client.get(f"/specialists/{specialist_id}/services")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["title"] == "Haircut"


def test_client_cannot_create_specialist_service(client):
    client_payload = {
        "email": "clientonly@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/specialists/me/services",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Should fail",
            "description": "No rights",
            "duration_minutes": 30,
            "price": "10.00",
        },
    )
    assert response.status_code == 403


def test_specialist_can_create_time_slot(client):
    specialist_payload = {
        "email": "slotspecialist@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    token = login.json()["access_token"]

    response = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": "2026-02-11T10:00:00Z", "end_at": "2026-02-11T11:00:00Z"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_booked"] is False
    assert data["specialist_id"] > 0


def test_slot_overlap_returns_409(client):
    specialist_payload = {
        "email": "overlap@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    token = login.json()["access_token"]

    first = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": "2026-02-12T10:00:00Z", "end_at": "2026-02-12T11:00:00Z"},
    )
    second = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": "2026-02-12T10:30:00Z", "end_at": "2026-02-12T11:30:00Z"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Time slot overlaps with existing slot"


def test_get_specialist_slots_by_date(client):
    specialist_payload = {
        "email": "listingslots@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    token = login.json()["access_token"]

    first_slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": "2026-02-13T09:00:00Z", "end_at": "2026-02-13T10:00:00Z"},
    ).json()
    client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": "2026-02-14T09:00:00Z", "end_at": "2026-02-14T10:00:00Z"},
    )

    specialist_id = first_slot["specialist_id"]
    response = client.get(f"/specialists/{specialist_id}/slots?date=2026-02-13")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["start_at"].startswith("2026-02-13T09:00:00")


def test_get_specialist_availability_aggregates_free_and_booked_slots(client):
    specialist_payload = {
        "email": "availabilityspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]

    first_day_slot_a = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-26T09:00:00Z", "end_at": "2026-02-26T10:00:00Z"},
    ).json()
    client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-26T11:00:00Z", "end_at": "2026-02-26T12:00:00Z"},
    )
    client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-27T09:00:00Z", "end_at": "2026-02-27T10:00:00Z"},
    )

    client_payload = {
        "email": "availabilityclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": first_day_slot_a["id"]},
    )

    specialist_id = first_day_slot_a["specialist_id"]
    response = client.get(
        f"/specialists/{specialist_id}/availability?date_from=2026-02-26&days=3"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3

    assert data[0] == {
        "date": "2026-02-26",
        "total_slots": 2,
        "free_slots": 1,
        "booked_slots": 1,
    }
    assert data[1] == {
        "date": "2026-02-27",
        "total_slots": 1,
        "free_slots": 1,
        "booked_slots": 0,
    }
    assert data[2] == {
        "date": "2026-02-28",
        "total_slots": 0,
        "free_slots": 0,
        "booked_slots": 0,
    }


def test_get_specialist_availability_returns_404_for_unknown_specialist(client):
    response = client.get("/specialists/999999/availability")

    assert response.status_code == 404
    assert response.json()["detail"] == "Specialist not found"


def test_specialist_can_delete_own_free_slot(client):
    specialist_payload = {
        "email": "deleteslotspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-28T10:00:00Z", "end_at": "2026-02-28T11:00:00Z"},
    ).json()

    delete_response = client.delete(
        f"/specialists/me/slots/{slot['id']}",
        headers={"Authorization": f"Bearer {specialist_token}"},
    )
    assert delete_response.status_code == 204

    slots_after_delete = client.get(
        f"/specialists/{slot['specialist_id']}/slots?date=2026-02-28"
    )
    assert slots_after_delete.status_code == 200
    assert slots_after_delete.json() == []


def test_specialist_cannot_delete_booked_slot(client):
    specialist_payload = {
        "email": "deletebookedspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-03-01T10:00:00Z", "end_at": "2026-03-01T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "deletebookedclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    booked = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    )
    assert booked.status_code == 201

    delete_response = client.delete(
        f"/specialists/me/slots/{slot['id']}",
        headers={"Authorization": f"Bearer {specialist_token}"},
    )
    assert delete_response.status_code == 409
    assert delete_response.json()["detail"] == "Booked slot cannot be deleted"


def test_booking_create_and_conflict(client):
    specialist_payload = {
        "email": "bookspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-15T10:00:00Z", "end_at": "2026-02-15T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "bookclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]

    first = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    )
    second = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    )

    assert first.status_code == 201
    assert first.json()["status"] == "confirmed"
    assert second.status_code == 409
    assert second.json()["detail"] == "Slot already booked"


def test_client_can_get_own_booking_by_id(client):
    specialist_payload = {
        "email": "bookingbyid-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-03-02T10:00:00Z", "end_at": "2026-03-02T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "bookingbyid-client@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    response = client.get(
        f"/bookings/{booking['id']}",
        headers={"Authorization": f"Bearer {client_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == booking["id"]
    assert data["slot_id"] == slot["id"]
    assert data["client_id"] > 0
    assert data["status"] == "confirmed"


def test_specialist_can_get_booking_for_own_slot(client):
    specialist_payload = {
        "email": "bookingbyid-ownspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-03-03T10:00:00Z", "end_at": "2026-03-03T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "bookingbyid-ownspec-client@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    response = client.get(
        f"/bookings/{booking['id']}",
        headers={"Authorization": f"Bearer {specialist_token}"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == booking["id"]


def test_other_client_cannot_get_foreign_booking_by_id(client):
    specialist_payload = {
        "email": "bookingbyid-deny-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-03-04T10:00:00Z", "end_at": "2026-03-04T11:00:00Z"},
    ).json()

    owner_payload = {
        "email": "bookingbyid-owner@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=owner_payload)
    owner_login = client.post(
        "/auth/login",
        json={"email": owner_payload["email"], "password": owner_payload["password"]},
    )
    owner_token = owner_login.json()["access_token"]
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    stranger_payload = {
        "email": "bookingbyid-stranger@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=stranger_payload)
    stranger_login = client.post(
        "/auth/login",
        json={"email": stranger_payload["email"], "password": stranger_payload["password"]},
    )
    stranger_token = stranger_login.json()["access_token"]

    denied = client.get(
        f"/bookings/{booking['id']}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not enough permissions"


def test_booking_create_is_idempotent_with_header(client):
    specialist_payload = {
        "email": "idem-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-15T12:00:00Z", "end_at": "2026-02-15T13:00:00Z"},
    ).json()

    client_payload = {
        "email": "idem-client@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {client_token}",
        "Idempotency-Key": "booking-idem-001",
    }

    first = client.post("/bookings", headers=headers, json={"slot_id": slot["id"]})
    second = client.post("/bookings", headers=headers, json={"slot_id": slot["id"]})

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    bookings = client.get("/bookings/me", headers={"Authorization": f"Bearer {client_token}"})
    assert bookings.status_code == 200
    assert len(bookings.json()) == 1


def test_booking_idempotency_key_reuse_with_different_slot_returns_409(client):
    specialist_payload = {
        "email": "idem-reuse-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot1 = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-15T14:00:00Z", "end_at": "2026-02-15T15:00:00Z"},
    ).json()
    slot2 = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-15T16:00:00Z", "end_at": "2026-02-15T17:00:00Z"},
    ).json()

    client_payload = {
        "email": "idem-reuse-client@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    headers = {
        "Authorization": f"Bearer {client_token}",
        "Idempotency-Key": "booking-idem-002",
    }

    first = client.post("/bookings", headers=headers, json={"slot_id": slot1["id"]})
    reused = client.post("/bookings", headers=headers, json={"slot_id": slot2["id"]})

    assert first.status_code == 201
    assert reused.status_code == 409
    assert reused.json()["detail"] == "Idempotency key already used with another slot"


def test_client_can_download_booking_calendar_file(client):
    specialist_payload = {
        "email": "calendar-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-22T10:00:00Z", "end_at": "2026-02-22T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "calendar-client@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]

    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    calendar_response = client.get(
        f"/bookings/{booking['id']}/calendar.ics",
        headers={"Authorization": f"Bearer {client_token}"},
    )

    assert calendar_response.status_code == 200
    assert calendar_response.headers["content-type"].startswith("text/calendar")
    assert (
        calendar_response.headers["content-disposition"]
        == f'attachment; filename="booking-{booking["id"]}.ics"'
    )
    body = calendar_response.text
    assert "BEGIN:VCALENDAR" in body
    assert "BEGIN:VEVENT" in body
    assert "SUMMARY:Booking with" in body
    assert "DTSTART:20260222T100000Z" in body
    assert "DTEND:20260222T110000Z" in body


def test_other_client_cannot_download_foreign_booking_calendar_file(client):
    specialist_payload = {
        "email": "calendar-deny-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-22T12:00:00Z", "end_at": "2026-02-22T13:00:00Z"},
    ).json()

    owner_payload = {
        "email": "calendar-owner@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=owner_payload)
    owner_login = client.post(
        "/auth/login",
        json={"email": owner_payload["email"], "password": owner_payload["password"]},
    )
    owner_token = owner_login.json()["access_token"]
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    stranger_payload = {
        "email": "calendar-stranger@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=stranger_payload)
    stranger_login = client.post(
        "/auth/login",
        json={"email": stranger_payload["email"], "password": stranger_payload["password"]},
    )
    stranger_token = stranger_login.json()["access_token"]

    denied = client.get(
        f"/bookings/{booking['id']}/calendar.ics",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not enough permissions"


def test_booking_cancel_frees_slot(client):
    specialist_payload = {
        "email": "cancelspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-16T10:00:00Z", "end_at": "2026-02-16T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "cancelclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]

    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    cancel = client.patch(
        f"/bookings/{booking['id']}/cancel",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    rebook = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    )

    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
    assert rebook.status_code == 201


def test_booking_reschedule_moves_booking_and_frees_old_slot(client):
    specialist_payload = {
        "email": "reschedulespec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot_a = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-23T10:00:00Z", "end_at": "2026-02-23T11:00:00Z"},
    ).json()
    slot_b = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-23T12:00:00Z", "end_at": "2026-02-23T13:00:00Z"},
    ).json()

    client_payload = {
        "email": "rescheduleclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot_a["id"]},
    ).json()

    rescheduled = client.patch(
        f"/bookings/{booking['id']}/reschedule",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot_b["id"]},
    )

    assert rescheduled.status_code == 200
    assert rescheduled.json()["slot_id"] == slot_b["id"]
    assert rescheduled.json()["status"] == "confirmed"

    other_payload = {
        "email": "rescheduleother@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=other_payload)
    other_login = client.post(
        "/auth/login",
        json={"email": other_payload["email"], "password": other_payload["password"]},
    )
    other_token = other_login.json()["access_token"]
    rebook_old = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {other_token}"},
        json={"slot_id": slot_a["id"]},
    )

    assert rebook_old.status_code == 201


def test_other_client_cannot_reschedule_foreign_booking(client):
    specialist_payload = {
        "email": "rescheduledeny-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot_a = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-24T10:00:00Z", "end_at": "2026-02-24T11:00:00Z"},
    ).json()
    slot_b = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-24T12:00:00Z", "end_at": "2026-02-24T13:00:00Z"},
    ).json()

    owner_payload = {
        "email": "reschedule-owner@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=owner_payload)
    owner_login = client.post(
        "/auth/login",
        json={"email": owner_payload["email"], "password": owner_payload["password"]},
    )
    owner_token = owner_login.json()["access_token"]
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"slot_id": slot_a["id"]},
    ).json()

    stranger_payload = {
        "email": "reschedule-stranger@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=stranger_payload)
    stranger_login = client.post(
        "/auth/login",
        json={"email": stranger_payload["email"], "password": stranger_payload["password"]},
    )
    stranger_token = stranger_login.json()["access_token"]
    denied = client.patch(
        f"/bookings/{booking['id']}/reschedule",
        headers={"Authorization": f"Bearer {stranger_token}"},
        json={"slot_id": slot_b["id"]},
    )

    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not enough permissions"


def test_reschedule_to_another_specialist_slot_returns_409(client):
    specialist_a_payload = {
        "email": "reschedule-spec-a@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_a_payload)
    specialist_a_login = client.post(
        "/auth/login",
        json={"email": specialist_a_payload["email"], "password": specialist_a_payload["password"]},
    )
    specialist_a_token = specialist_a_login.json()["access_token"]
    slot_a = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_a_token}"},
        json={"start_at": "2026-02-25T10:00:00Z", "end_at": "2026-02-25T11:00:00Z"},
    ).json()

    specialist_b_payload = {
        "email": "reschedule-spec-b@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_b_payload)
    specialist_b_login = client.post(
        "/auth/login",
        json={"email": specialist_b_payload["email"], "password": specialist_b_payload["password"]},
    )
    specialist_b_token = specialist_b_login.json()["access_token"]
    slot_b = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_b_token}"},
        json={"start_at": "2026-02-25T12:00:00Z", "end_at": "2026-02-25T13:00:00Z"},
    ).json()

    client_payload = {
        "email": "reschedule-cross-client@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot_a["id"]},
    ).json()

    reschedule = client.patch(
        f"/bookings/{booking['id']}/reschedule",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot_b["id"]},
    )

    assert reschedule.status_code == 409
    assert reschedule.json()["detail"] == "New slot must belong to the same specialist"


def test_list_my_bookings(client):
    specialist_payload = {
        "email": "mybookspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-17T10:00:00Z", "end_at": "2026-02-17T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "mybookclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    )

    response = client.get("/bookings/me", headers={"Authorization": f"Bearer {client_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["slot_id"] == slot["id"]


def test_list_my_bookings_with_filters(client):
    specialist_payload = {
        "email": "filterbookspec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot_a = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-18T10:00:00Z", "end_at": "2026-02-18T11:00:00Z"},
    ).json()
    slot_b = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-20T10:00:00Z", "end_at": "2026-02-20T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "filterbookclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]

    b1 = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot_a["id"]},
    ).json()
    client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot_b["id"]},
    )
    client.patch(
        f"/bookings/{b1['id']}/cancel",
        headers={"Authorization": f"Bearer {client_token}"},
    )

    confirmed = client.get(
        "/bookings/me?status=confirmed",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    date_filtered = client.get(
        "/bookings/me?date_from=2026-02-20&date_to=2026-02-20",
        headers={"Authorization": f"Bearer {client_token}"},
    )

    assert confirmed.status_code == 200
    assert len(confirmed.json()) == 1
    assert confirmed.json()[0]["status"] == "confirmed"
    assert date_filtered.status_code == 200
    assert len(date_filtered.json()) == 1
    assert date_filtered.json()[0]["slot_id"] == slot_b["id"]


def test_specialist_can_list_own_bookings(client):
    specialist_payload = {
        "email": "speccabinet@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    specialist_login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    specialist_token = specialist_login.json()["access_token"]
    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-02-21T10:00:00Z", "end_at": "2026-02-21T11:00:00Z"},
    ).json()

    client_payload = {
        "email": "speccabinetclient@example.com",
        "password": "StrongPass123",
        "role": "client",
    }
    client.post("/auth/register", json=client_payload)
    client_login = client.post(
        "/auth/login",
        json={"email": client_payload["email"], "password": client_payload["password"]},
    )
    client_token = client_login.json()["access_token"]
    booked = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    specialist_view = client.get(
        "/bookings/specialists/me",
        headers={"Authorization": f"Bearer {specialist_token}"},
    )

    assert specialist_view.status_code == 200
    data = specialist_view.json()
    assert len(data) == 1
    assert data[0]["id"] == booked["id"]
    assert data[0]["client_email"] == client_payload["email"]
    assert data[0]["slot_start_at"].startswith("2026-02-21T10:00:00")
    assert data[0]["slot_end_at"].startswith("2026-02-21T11:00:00")

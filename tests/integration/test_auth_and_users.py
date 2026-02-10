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

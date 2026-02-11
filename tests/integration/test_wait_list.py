def _register_and_login(client, email: str, role: str) -> str:
    payload = {"email": email, "password": "StrongPass123", "role": role}
    register_response = client.post("/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    return login_response.json()["access_token"]


def test_client_can_join_wait_list_for_booked_slot(client):
    specialist_token = _register_and_login(client, "wl-spec@example.com", "specialist")
    client1_token = _register_and_login(client, "wl-client-1@example.com", "client")
    client2_token = _register_and_login(client, "wl-client-2@example.com", "client")

    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-04-01T10:00:00Z", "end_at": "2026-04-01T11:00:00Z"},
    ).json()

    booking_response = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client1_token}"},
        json={"slot_id": slot["id"]},
    )
    assert booking_response.status_code == 201

    wait_list_response = client.post(
        "/bookings/wait-list",
        headers={"Authorization": f"Bearer {client2_token}"},
        json={"slot_id": slot["id"]},
    )
    assert wait_list_response.status_code == 201
    data = wait_list_response.json()
    assert data["slot_id"] == slot["id"]


def test_wait_list_rejects_available_slot(client):
    specialist_token = _register_and_login(client, "wl-available-spec@example.com", "specialist")
    client_token = _register_and_login(client, "wl-available-client@example.com", "client")

    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-04-02T10:00:00Z", "end_at": "2026-04-02T11:00:00Z"},
    ).json()

    response = client.post(
        "/bookings/wait-list",
        headers={"Authorization": f"Bearer {client_token}"},
        json={"slot_id": slot["id"]},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Slot is available. Book directly"


def test_cancelling_booking_promotes_first_wait_list_entry(client):
    specialist_token = _register_and_login(client, "wl-promote-spec@example.com", "specialist")
    client1_token = _register_and_login(client, "wl-promote-client-1@example.com", "client")
    client2_token = _register_and_login(client, "wl-promote-client-2@example.com", "client")

    slot = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {specialist_token}"},
        json={"start_at": "2026-04-03T10:00:00Z", "end_at": "2026-04-03T11:00:00Z"},
    ).json()

    booking = client.post(
        "/bookings",
        headers={"Authorization": f"Bearer {client1_token}"},
        json={"slot_id": slot["id"]},
    ).json()

    wait_list = client.post(
        "/bookings/wait-list",
        headers={"Authorization": f"Bearer {client2_token}"},
        json={"slot_id": slot["id"]},
    )
    assert wait_list.status_code == 201

    cancel_response = client.patch(
        f"/bookings/{booking['id']}/cancel",
        headers={"Authorization": f"Bearer {client1_token}"},
    )
    assert cancel_response.status_code == 200

    promoted_bookings = client.get(
        "/bookings/me",
        headers={"Authorization": f"Bearer {client2_token}"},
    )
    assert promoted_bookings.status_code == 200
    promoted_data = promoted_bookings.json()
    assert len(promoted_data) == 1
    assert promoted_data[0]["slot_id"] == slot["id"]
    assert promoted_data[0]["status"] == "confirmed"

    my_wait_list = client.get(
        "/bookings/wait-list/me",
        headers={"Authorization": f"Bearer {client2_token}"},
    )
    assert my_wait_list.status_code == 200
    assert my_wait_list.json() == []

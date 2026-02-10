def test_error_response_has_unified_shape(client):
    response = client.get("/users/me")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert "detail" in body
    assert "request_id" in body


def test_health_endpoint_returns_ok_and_request_id(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "x-request-id" in response.headers


def test_slots_pagination_limit_offset(client):
    specialist_payload = {
        "email": "pagination-spec@example.com",
        "password": "StrongPass123",
        "role": "specialist",
    }
    client.post("/auth/register", json=specialist_payload)
    login = client.post(
        "/auth/login",
        json={"email": specialist_payload["email"], "password": specialist_payload["password"]},
    )
    token = login.json()["access_token"]

    slot1 = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": "2026-03-01T10:00:00Z", "end_at": "2026-03-01T11:00:00Z"},
    ).json()
    slot2 = client.post(
        "/specialists/me/slots",
        headers={"Authorization": f"Bearer {token}"},
        json={"start_at": "2026-03-01T12:00:00Z", "end_at": "2026-03-01T13:00:00Z"},
    ).json()

    specialist_id = slot1["specialist_id"]
    paged = client.get(f"/specialists/{specialist_id}/slots?limit=1&offset=1")
    assert paged.status_code == 200
    data = paged.json()
    assert len(data) == 1
    assert data[0]["id"] == slot2["id"]

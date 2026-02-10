from app.core.config import settings
from app.core.rate_limiter import rate_limiter


def test_register_rate_limit_returns_429(client):
    original_limit = settings.auth_register_max_attempts
    original_window = settings.auth_rate_limit_window_seconds
    settings.auth_register_max_attempts = 2
    settings.auth_rate_limit_window_seconds = 60
    rate_limiter.reset()
    try:
        first = client.post(
            "/auth/register",
            json={"email": "limit1@example.com", "password": "StrongPass123", "role": "client"},
        )
        second = client.post(
            "/auth/register",
            json={"email": "limit2@example.com", "password": "StrongPass123", "role": "client"},
        )
        third = client.post(
            "/auth/register",
            json={"email": "limit3@example.com", "password": "StrongPass123", "role": "client"},
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert third.status_code == 429
        assert "error" in third.json()
        assert third.headers.get("Retry-After")
    finally:
        settings.auth_register_max_attempts = original_limit
        settings.auth_rate_limit_window_seconds = original_window
        rate_limiter.reset()


def test_login_rate_limit_returns_429(client):
    original_limit = settings.auth_login_max_attempts
    original_window = settings.auth_rate_limit_window_seconds
    settings.auth_login_max_attempts = 2
    settings.auth_rate_limit_window_seconds = 60
    rate_limiter.reset()
    try:
        client.post(
            "/auth/register",
            json={"email": "loglimit@example.com", "password": "StrongPass123", "role": "client"},
        )

        first = client.post("/auth/login", json={"email": "loglimit@example.com", "password": "WrongPass123"})
        second = client.post("/auth/login", json={"email": "loglimit@example.com", "password": "WrongPass123"})
        third = client.post("/auth/login", json={"email": "loglimit@example.com", "password": "WrongPass123"})

        assert first.status_code == 401
        assert second.status_code == 401
        assert third.status_code == 429
        assert third.json()["error"]["code"] == "http_429"
    finally:
        settings.auth_login_max_attempts = original_limit
        settings.auth_rate_limit_window_seconds = original_window
        rate_limiter.reset()

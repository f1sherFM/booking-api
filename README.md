# Booking API

Backend-сервис для онлайн-записи к специалистам (barber/tutor/trainer) с защитой от двойного бронирования слотов.

## Status
- Backend MVP готов.
- Покрыты ключевые сценарии auth -> services -> slots -> bookings.
- Добавлены observability, rate limit и CI.
- Тестовый статус: `25 passed`.

## Tech Stack
- Python 3.12
- FastAPI
- PostgreSQL
- Redis
- Celery + Celery Beat
- SQLAlchemy + Alembic
- Docker + Docker Compose
- Pytest
- GitHub Actions
- Prometheus client

## Architecture (high-level)
- `API layer` (`app/api/v1`)  
  HTTP endpoints, auth dependencies, validation, pagination params.
- `Domain/services layer` (`app/services`)  
  Бизнес-логика (включая concurrency-safe бронирование).
- `Persistence layer` (`app/db`)  
  SQLAlchemy модели, сессии, миграции Alembic.
- `Background layer` (`app/tasks`)  
  Периодические задачи Celery (истечения и напоминания).
- `Cross-cutting` (`app/core`)  
  config, security, rate limiting, error handlers, logging, metrics.

## Run (Docker)
```bash
cp .env.example .env
docker compose up --build -d
docker compose run --rm api alembic upgrade head
```

API:
- `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Tests
```bash
docker compose run --rm api pytest -q
```

## CI
- Workflow: `.github/workflows/ci.yml`
- На каждый `push` и `pull_request`: install -> compile -> test

## Core API
Auth:
- `POST /auth/register`
- `POST /auth/login`

Users:
- `GET /users/me`
- `GET /users` (admin)

Specialists:
- `POST /specialists/me/services` (specialist/admin)
- `GET /specialists/{id}/services`
- `POST /specialists/me/slots` (specialist/admin)
- `GET /specialists/{id}/slots?date=YYYY-MM-DD`

Bookings:
- `POST /bookings` (client/admin)
- `PATCH /bookings/{id}/cancel`
- `GET /bookings/me`
- `GET /bookings/specialists/me`

List endpoints support:
- `limit`
- `offset`

Bookings filters:
- `status=confirmed|cancelled|expired`
- `date_from=YYYY-MM-DD`
- `date_to=YYYY-MM-DD`

## Background Tasks
- `bookings.expire_started_slots`  
  Переводит устаревшие `confirmed` в `expired` и освобождает слот.
- `bookings.remind_upcoming`  
  Считает брони в окне напоминаний.

## Observability
- `GET /metrics` (Prometheus)
- `X-Request-ID` в каждом ответе
- Request logs: method, path, status, duration, request_id

## Security
- Rate limit для:
  - `POST /auth/register`
  - `POST /auth/login`
- Backend for rate limit:
  - Redis (primary, production)
  - In-memory fallback (if Redis is temporarily unavailable)
- При превышении:
  - HTTP `429`
  - заголовок `Retry-After`

## Error Response Shape
```json
{
  "error": {
    "code": "http_404",
    "message": "Slot not found",
    "detail": "Slot not found"
  },
  "detail": "Slot not found",
  "request_id": "..."
}
```

## Smoke Check
Смотри файл: `SMOKE_CHECKLIST.md`

## Project Structure
```txt
app/
  api/
  core/
  db/
  schemas/
  services/
  tasks/
  main.py
migrations/
tests/
docker/
.github/workflows/
```

## Environment
Все переменные и значения по умолчанию: `.env.example`

## License
MIT

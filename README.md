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
- Health: `http://localhost:8000/health`

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
- `DELETE /specialists/me/slots/{id}` (specialist/admin, only free slot)
- `GET /specialists/{id}/slots?date=YYYY-MM-DD`
- `GET /specialists/{id}/availability?date_from=YYYY-MM-DD&days=7`

Bookings:
- `POST /bookings` (client/admin)
- `GET /bookings/{id}`
- `PATCH /bookings/{id}/cancel`
- `PATCH /bookings/{id}/reschedule`
- `GET /bookings/{id}/calendar.ics`
- `GET /bookings/me`
- `GET /bookings/specialists/me`
- `POST /bookings/wait-list`
- `GET /bookings/wait-list/me`
- `DELETE /bookings/wait-list/{entry_id}`

List endpoints support:
- `limit`
- `offset`

Bookings filters:
- `status=confirmed|cancelled|expired`
- `date_from=YYYY-MM-DD`
- `date_to=YYYY-MM-DD`

Specialist bookings list (`GET /bookings/specialists/me`) includes summary fields:
- `client_email`
- `slot_start_at`
- `slot_end_at`

## Background Tasks
- `bookings.expire_started_slots`  
  Переводит устаревшие `confirmed` в `expired`, освобождает слот и пытается автоматически продвинуть первого клиента из wait list.
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

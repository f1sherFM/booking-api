# Smoke Checklist (Release)

## Preconditions
- Containers are running:
  - `docker compose up -d`
- Migrations are applied:
  - `docker compose run --rm api alembic upgrade head`

## 1. Health and Docs
- `GET /health` -> `200`
- `GET /docs` opens
- `GET /metrics` -> `200` and contains:
  - `http_requests_total`
  - `http_request_duration_seconds`

## 2. Auth Flow
- `POST /auth/register` with unique email -> `201`
- `POST /auth/login` with same credentials -> `200` and `access_token`
- Use token in Swagger `Authorize` as `Bearer <token>`

## 3. Specialist Setup
- Register specialist user (`role=specialist`)
- Login as specialist
- `POST /specialists/me/services` -> `201`
- `POST /specialists/me/slots` -> `201`
- `GET /specialists/{id}/slots?date=...` -> created slot is visible

## 4. Booking Flow
- Register client user (`role=client`)
- Login as client
- `POST /bookings` with specialist slot -> `201`
- Repeat same request -> `409` (`Slot already booked`)
- `PATCH /bookings/{id}/cancel` -> `200`
- `POST /bookings` same slot again -> `201`

## 5. Access Rules
- Client tries `POST /specialists/me/services` -> `403`
- Unauthenticated call to `GET /users/me` -> `401`

## 6. Error Shape
For any expected error response confirm fields:
- `error.code`
- `error.message`
- `error.detail`
- `request_id`

## 7. Rate Limiting
- Multiple rapid `/auth/login` attempts should eventually return:
  - `429`
  - `Retry-After` header

## 8. Automated Validation
- Run:
  - `docker compose run --rm api pytest -q`
- Expected: all tests pass

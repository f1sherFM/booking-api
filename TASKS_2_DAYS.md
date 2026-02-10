# TASKS: ближайшие 2 дня

## Цель
Сделать первый рабочий кусок продукта: `Auth + User model + базовые тесты`, чтобы проект уже выглядел как реальный backend, а не только каркас.

## День 1 (Auth фундамент)

### 1. Подготовить структуру auth
- [ ] Создать файлы:
  - `app/core/config.py`
  - `app/core/security.py`
  - `app/db/session.py`
  - `app/db/base.py`
  - `app/db/models/user.py`
  - `app/schemas/auth.py`
  - `app/schemas/user.py`
  - `app/api/v1/auth.py`
  - `app/services/auth_service.py`

### 2. Подключить БД и модель User
- [ ] Добавить SQLAlchemy engine/session
- [ ] Описать модель `User`:
  - `id`
  - `email` (unique)
  - `hashed_password`
  - `role` (`client/specialist/admin`)
  - `is_active`
  - `created_at`

### 3. Настроить Alembic
- [ ] Инициализировать/донастроить Alembic
- [ ] Создать миграцию под таблицу `users`
- [ ] Применить миграцию

### 4. Реализовать JWT + hash пароля
- [ ] `passlib` для hash/verify
- [ ] Создание access token
- [ ] Валидация токена

### 5. Эндпоинты auth
- [x] `POST /auth/register`
- [x] `POST /auth/login`
- [x] Подключить роутер в `app/main.py`

### Definition of done (День 1)
- [x] Регистрация возвращает созданного пользователя
- [x] Логин возвращает access token
- [x] Дублирующийся email даёт 409/400
- [x] `/docs` показывает auth эндпоинты

---

## День 2 (Качество + доступ)

### 1. Текущий пользователь
- [x] Добавить dependency `get_current_user`
- [x] Добавить `GET /users/me`

### 2. Роли и ограничения доступа
- [x] Сделать проверку роли (RBAC helper)
- [x] Заготовить пример admin-only endpoint (`GET /users`)

### 3. Тесты
- [x] Unit: hash/verify password
- [x] Integration:
  - [x] register success
  - [x] register duplicate email
  - [x] login success
  - [x] users/me with token
  - [x] users/me without token (401)

### 4. DX и документация
- [ ] Обновить `README.md` разделами:
  - новые endpoints
  - как запустить миграции
  - как прогнать тесты
- [ ] Добавить короткий changelog-блок “что сделано за 2 дня”

### Definition of done (День 2)
- [ ] Есть рабочий JWT flow
- [x] Есть минимум 5 тестов, проходящих локально
- [ ] README актуален и отражает текущее состояние

---

## Быстрые команды

```bash
# запуск проекта
docker compose up --build

# миграции
docker compose run --rm api alembic revision --autogenerate -m "create users table"
docker compose run --rm api alembic upgrade head

# тесты
docker compose run --rm api pytest -q
```

## Результат через 2 дня
Ты получишь первую "продаваемую" версию backend-части: нормальный auth, пользователи, роли и базовый test coverage.

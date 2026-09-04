# Soborbum — бэкенд

FastAPI-бэкенд для управления производством модульных домов: полный цикл клиента
(клиенты → производство → монтаж), склад, маркетинг и сквозные задачи сотрудников.

## Запуск

```bash
docker compose up --build
```

Поднимутся `db` (PostgreSQL) и `backend` (FastAPI, с автоперезагрузкой на dev-запуске).
При первом старте контейнер сам сгенерирует и применит миграции Alembic и создаст
администратора из переменных окружения `ADMIN_EMAIL` / `ADMIN_PASSWORD`
(по умолчанию `admin@soborbum.local` / `admin123`, см. `.env.example`).

## Разделы API

Каждый раздел — отдельное FastAPI-приложение со своей Swagger-документацией:

| Раздел | Swagger UI |
| --- | --- |
| Аутентификация и пользователи | http://localhost:8000/api/auth/docs |
| Клиенты | http://localhost:8000/api/clients/docs |
| Производство | http://localhost:8000/api/production/docs |
| Монтаж | http://localhost:8000/api/installation/docs |
| Цикл клиента | http://localhost:8000/api/cycles/docs |
| Склад | http://localhost:8000/api/warehouse/docs |
| Маркетинг | http://localhost:8000/api/marketing/docs |
| Задачи | http://localhost:8000/api/tasks/docs |
| ИИ-ассистент | http://localhost:8000/api/ai/docs |
| Совет директоров | http://localhost:8000/api/board/docs |

Авторизация — JWT: `POST /api/auth/login` (форма `username`/`password`), затем
`Authorize` в любом Swagger UI с полученным токеном (действует на все разделы,
т.к. проверяется общим образом через `/api/auth/login`).

## Структура проекта

Код организован по разделам (vertical slices), а не по техническому слою —
у каждого раздела один файл на слой (`models.py`, `schemas.py`, `service.py`,
`router.py`), и большая часть логики раздела лежит в одной папке:

```
app/
  core/      конфиг, JWT, зависимости доступа (общие для всех разделов)
  db/        подключение к БД
  common/    Module enum (доступ) и хранение файлов (используются всеми разделами)
  users/     аутентификация, пользователи, матрица доступа
  tasks/     общий движок задач + синхронизация со всеми разделами
  cycle/     сквозной агрегатор клиент+производство+монтаж
  clients/   клиенты (лид → постоплата)
  production/ модули дома, материалы, заявки на материалы
  installation/ монтаж (доставка → установка → проработка)
  warehouse/ склад, поставки, история движения материалов
  marketing/ календарь контента
```

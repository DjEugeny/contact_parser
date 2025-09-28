# API контракты (минимум для MVP)

Базовый URL: `/api/v1`

## Auth
- `POST /auth/login` — email+password или Google OAuth callback.
- `GET /auth/me` — текущий пользователь.

## Search
- `GET /contacts` — фильтры: `q, city, org_id, phone, email`.
- `GET /organizations` — фильтры: `q, city, inn, has_active_offers`.
- `GET /offers` — фильтры: `org_id, status, valid_from, valid_to, end_user, intermediary`.

## Entities
- `GET/POST/PATCH /contacts/:id`
- `GET/POST/PATCH /organizations/:id`
- `GET/POST/PATCH /offers/:id`

## Interactions
- `GET /interactions?contact_id=&org_id=` — лента взаимодействий.

## Files
- `GET /emails/:id/download-eml` — отдаёт `.eml`.
- `GET /attachments/:id/download` — отдаёт файл.

## Moderation
- `GET /moderation` — очередь.
- `POST /moderation/:id/accept` — применить изменения.
- `POST /moderation/:id/merge` — объединить с существующей записью.

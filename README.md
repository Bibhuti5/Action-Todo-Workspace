# Email Summary Platform (Python + AWS + Microsoft 365)

Production-oriented microservice starter for:
- scanning Office/Microsoft 365 mail at **11:00 AM** and **5:00 PM**
- building a daily summary for dashboard
- pushing action-required items into notifications

This scaffold is intentionally simple for V1 but structured for production growth.

## Services

- `gateway`: frontend/BFF API for dashboard, actions, notifications, run-now.
- `scheduler`: recurring job runner (11:00 + 17:00) per timezone.
- `auth`: Microsoft OAuth code exchange + token storage/refresh.
- `ingestion`: fetches mail from Microsoft Graph using delegated user token.
- `summarizer`: builds digest + action detection and stores results.
- `notifier`: stores and serves in-app notifications.
- `shared/python/email_core`: shared models and logging utilities.

## Repository Layout

```text
services/
  auth/
  gateway/
  scheduler/
  ingestion/
  summarizer/
  notifier/
shared/python/email_core/
infra/aws/
docker-compose.yml
```

## Local Run

1. Copy env template:
   - `copy .env.example .env` (PowerShell)
2. Start services:
   - `docker compose up --build`
3. Open API:
   - Gateway: `http://localhost:8000/docs`
   - Scheduler: `http://localhost:8010/docs`

## MVP API (Gateway)

- `GET /api/mail/connect/microsoft365` (returns Microsoft authorize URL)
- `GET /api/mail/oauth/callback?code=...&state=...`
- `GET /api/dashboard/today`
- `GET /api/actions?status=open&priority=high`
- `GET /api/notifications?status=unread`
- `POST /api/notifications/{id}/read`
- `POST /api/scans/run-now`

All user-scoped gateway APIs require `X-User-Id` header.

## Connect Office 365 (Quick Flow)

1. Call `GET /api/mail/connect/microsoft365` with header `X-User-Id`.
2. Open returned `authorization_url` in browser and grant consent.
3. Microsoft redirects to `/api/mail/oauth/callback` and token is stored by `auth` service.
4. Scheduled/manual scans now read real mailbox messages.

## Next Build Steps

1. Replace shared SQLite with managed PostgreSQL (RDS) and service-owned schemas.
2. Add SQS pipeline between ingestion -> summarize/notify workers.
3. Move schedule execution to EventBridge Scheduler + ECS/Lambda target.
4. Add JWT-based auth + RBAC (replace simple header identity).
5. Add React/Next dashboard frontend.

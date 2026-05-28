# Email Summary Platform (Python + AWS + Microsoft 365)

Production-oriented microservice starter for:
- scanning Office/Microsoft 365 mail at **11:00 AM** and **5:00 PM**
- building a daily summary for dashboard
- pushing action-required items into notifications

This scaffold is intentionally simple for V1 but structured for production growth.

## Services

- `gateway`: frontend/BFF API for dashboard, actions, notifications, run-now.
- `scheduler`: recurring job runner (11:00 + 17:00) per timezone.
- `ingestion`: fetches mail (stubbed Microsoft Graph client for now).
- `summarizer`: builds digest + action detection (rule-based placeholder).
- `notifier`: stores and serves in-app notifications.
- `shared/python/email_core`: shared models and logging utilities.

## Repository Layout

```text
services/
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

- `GET /api/dashboard/today`
- `GET /api/actions?status=open&priority=high`
- `GET /api/notifications?status=unread`
- `POST /api/notifications/{id}/read`
- `POST /api/scans/run-now`

## Next Build Steps

1. Replace ingestion stub with Microsoft Graph delegated auth flow.
2. Store scans/emails/actions in PostgreSQL (RDS).
3. Use SQS between ingestion/summarizer/notifier.
4. Move schedule execution to EventBridge Scheduler + Lambda/ECS target.
5. Add React/Next dashboard frontend.


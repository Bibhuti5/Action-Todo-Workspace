# AWS Production Scheduling Notes

For production on AWS, replace in-process APScheduler with EventBridge Scheduler.

## Desired Schedules

- 11:00 local timezone daily
- 17:00 local timezone daily

Use two cron schedules and set timezone per tenant/user policy.

Examples:
- `cron(0 11 * * ? *)`
- `cron(0 17 * * ? *)`

Set `ScheduleExpressionTimezone` (for example, `Asia/Kolkata`) so the trigger runs in business local time.

## Target Options

- ECS task that hits gateway `/api/scans/run-now`
- Lambda that publishes scan event to SQS

## Recommended Runtime Flow

1. EventBridge Scheduler fires.
2. Pushes message to SQS queue (`email-summary-events`).
3. Ingestion worker consumes queue and runs Microsoft Graph mailbox pull.
4. Summarizer creates digest + actions.
5. Notifier creates unread notification records.


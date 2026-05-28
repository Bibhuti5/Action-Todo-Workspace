from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from email_core.logging import configure_logging
from email_core.models import CreateNotificationRequest, NotificationItem

from app.settings import settings

app = FastAPI(title="email-summary-notifier", version="0.1.0")
configure_logging(settings.service_name)

NOTIFICATIONS: list[NotificationItem] = []


@app.get("/internal/notifications", response_model=list[NotificationItem])
async def list_notifications(status: str = Query(default="unread")) -> list[NotificationItem]:
    if status == "all":
        return NOTIFICATIONS
    if status == "unread":
        return [item for item in NOTIFICATIONS if not item.is_read]
    if status == "read":
        return [item for item in NOTIFICATIONS if item.is_read]
    return NOTIFICATIONS


@app.post("/internal/notifications", response_model=NotificationItem)
async def create_notification(request: CreateNotificationRequest) -> NotificationItem:
    note = NotificationItem(
        id=str(uuid4()),
        user_id=request.user_id,
        title=request.title,
        body=request.body,
        related_email_id=request.related_email_id,
        created_at=datetime.now(timezone.utc),
    )
    NOTIFICATIONS.insert(0, note)
    return note


@app.post("/internal/notifications/{notification_id}/read", response_model=NotificationItem)
async def mark_read(notification_id: str) -> NotificationItem:
    for idx, item in enumerate(NOTIFICATIONS):
        if item.id == notification_id:
            updated = item.model_copy(update={"is_read": True})
            NOTIFICATIONS[idx] = updated
            return updated
    raise HTTPException(status_code=404, detail="notification_not_found")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name, "count": len(NOTIFICATIONS)}


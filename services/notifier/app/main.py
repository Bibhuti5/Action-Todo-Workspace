from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import desc, func, select

from email_core.logging import configure_logging
from email_core.models import CreateNotificationRequest, NotificationItem
from email_core.storage import NotificationRecord, init_db, session_scope

from app.settings import settings


def item_from_record(record: NotificationRecord) -> NotificationItem:
    return NotificationItem(
        id=record.id,
        user_id=record.user_id,
        type=record.type,
        title=record.title,
        body=record.body,
        related_email_id=record.related_email_id,
        is_read=record.is_read,
        created_at=record.created_at,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)
    init_db()
    yield


app = FastAPI(title="email-summary-notifier", version="0.1.0", lifespan=lifespan)


@app.get("/internal/notifications", response_model=list[NotificationItem])
async def list_notifications(
    user_id: str = Query(...),
    status: str = Query(default="unread"),
) -> list[NotificationItem]:
    with session_scope() as session:
        stmt = select(NotificationRecord).where(NotificationRecord.user_id == user_id)
        if status == "unread":
            stmt = stmt.where(NotificationRecord.is_read.is_(False))
        elif status == "read":
            stmt = stmt.where(NotificationRecord.is_read.is_(True))
        stmt = stmt.order_by(desc(NotificationRecord.created_at))
        rows = session.execute(stmt).scalars().all()
        return [item_from_record(item) for item in rows]


@app.post("/internal/notifications", response_model=NotificationItem)
async def create_notification(request: CreateNotificationRequest) -> NotificationItem:
    with session_scope() as session:
        record = NotificationRecord(
            id=str(uuid4()),
            user_id=request.user_id,
            type="action_required",
            title=request.title,
            body=request.body,
            related_email_id=request.related_email_id,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        session.add(record)
        session.flush()
        return item_from_record(record)


@app.post("/internal/notifications/{notification_id}/read", response_model=NotificationItem)
async def mark_read(
    notification_id: str,
    user_id: str = Query(...),
) -> NotificationItem:
    with session_scope() as session:
        record = session.get(NotificationRecord, notification_id)
        if record is None or record.user_id != user_id:
            raise HTTPException(status_code=404, detail="notification_not_found")
        record.is_read = True
        session.flush()
        return item_from_record(record)


@app.get("/health")
async def health() -> dict:
    with session_scope() as session:
        count = session.execute(select(func.count(NotificationRecord.id))).scalar_one()
    return {"status": "ok", "service": settings.service_name, "count": count}

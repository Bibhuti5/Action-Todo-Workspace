import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Query
from sqlalchemy import desc, select

from email_core.logging import configure_logging
from email_core.models import ActionType, DailySummary, EmailAction, Priority, ScanResult
from email_core.storage import ActionRecord, SummaryRecord, init_db, session_scope

from app.settings import settings


def classify(subject: str, snippet: str) -> tuple[ActionType, Priority, float]:
    text = f"{subject} {snippet}".lower()
    urgent_keywords = ("urgent", "asap", "today", "eod", "deadline")
    action_keywords = ("action required", "approve", "review", "respond", "reply")
    info_keywords = ("report", "newsletter", "update", "digest")

    if any(k in text for k in urgent_keywords):
        return (ActionType.urgent_action, Priority.high, 0.91)
    if any(k in text for k in action_keywords):
        return (ActionType.needs_reply, Priority.medium, 0.84)
    if any(k in text for k in info_keywords):
        return (ActionType.fyi, Priority.low, 0.78)
    return (ActionType.low_priority, Priority.low, 0.70)


def action_from_record(record: ActionRecord) -> EmailAction:
    return EmailAction(
        email_id=record.email_id,
        subject=record.subject,
        sender=record.sender,
        action_type=ActionType(record.action_type),
        priority=Priority(record.priority),
        confidence=record.confidence,
        due_hint=record.due_hint,
        status=record.status,
    )


def summary_from_record(record: SummaryRecord, actions: list[EmailAction]) -> DailySummary:
    return DailySummary(
        user_id=record.user_id,
        scan_run_id=record.scan_run_id,
        summary_text=record.summary_text,
        scanned_count=record.scanned_count,
        action_required_count=record.action_required_count,
        urgent_count=record.urgent_count,
        awaiting_reply_count=record.awaiting_reply_count,
        top_senders=json.loads(record.top_senders_json or "[]"),
        actions=actions,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)
    init_db()
    yield


app = FastAPI(title="email-summary-summarizer", version="0.1.0", lifespan=lifespan)


@app.post("/internal/process-scan", response_model=DailySummary)
async def process_scan(scan: ScanResult) -> DailySummary:
    actions: list[EmailAction] = []
    urgent_count = 0
    awaiting_reply = 0
    action_required = 0

    for email in scan.emails:
        action_type, priority, confidence = classify(email.subject, email.snippet)
        due_hint = "Before end of day" if priority == Priority.high else None
        action = EmailAction(
            email_id=email.provider_message_id,
            subject=email.subject,
            sender=email.sender,
            action_type=action_type,
            priority=priority,
            confidence=confidence,
            due_hint=due_hint,
        )
        actions.append(action)

        if action_type == ActionType.urgent_action:
            urgent_count += 1
        if action_type in (ActionType.urgent_action, ActionType.needs_reply):
            action_required += 1
            awaiting_reply += 1 if action_type == ActionType.needs_reply else 0

    top_senders = sorted({e.sender for e in scan.emails})[:5]
    summary_text = (
        f"Scanned {len(scan.emails)} emails. "
        f"{action_required} need attention, including {urgent_count} urgent items."
    )

    with session_scope() as session:
        summary_record = SummaryRecord(
            user_id=scan.user_id,
            scan_run_id=scan.scan_run_id,
            summary_text=summary_text,
            scanned_count=len(scan.emails),
            action_required_count=action_required,
            urgent_count=urgent_count,
            awaiting_reply_count=awaiting_reply,
            top_senders_json=json.dumps(top_senders),
            created_at=datetime.now(timezone.utc),
        )
        session.add(summary_record)

        for action in actions:
            session.add(
                ActionRecord(
                    user_id=scan.user_id,
                    scan_run_id=scan.scan_run_id,
                    email_id=action.email_id,
                    subject=action.subject,
                    sender=action.sender,
                    action_type=action.action_type.value,
                    priority=action.priority.value,
                    confidence=action.confidence,
                    due_hint=action.due_hint,
                    status=action.status,
                    created_at=datetime.now(timezone.utc),
                )
            )

    return DailySummary(
        user_id=scan.user_id,
        scan_run_id=scan.scan_run_id,
        summary_text=summary_text,
        scanned_count=len(scan.emails),
        action_required_count=action_required,
        urgent_count=urgent_count,
        awaiting_reply_count=awaiting_reply,
        top_senders=top_senders,
        actions=actions,
    )


@app.get("/internal/summary/today", response_model=DailySummary)
async def get_today_summary(user_id: str = Query(...)) -> DailySummary:
    with session_scope() as session:
        record = session.execute(
            select(SummaryRecord)
            .where(SummaryRecord.user_id == user_id)
            .order_by(desc(SummaryRecord.created_at))
            .limit(1)
        ).scalar_one_or_none()

        if record is None:
            return DailySummary(
                user_id=user_id,
                scan_run_id=f"empty-{datetime.now(timezone.utc).isoformat()}",
                summary_text="No scan has run yet today.",
                scanned_count=0,
                action_required_count=0,
                urgent_count=0,
                awaiting_reply_count=0,
                top_senders=[],
                actions=[],
            )

        action_records = session.execute(
            select(ActionRecord)
            .where(
                ActionRecord.user_id == user_id,
                ActionRecord.scan_run_id == record.scan_run_id,
            )
            .order_by(desc(ActionRecord.created_at))
        ).scalars()
        actions = [action_from_record(item) for item in action_records]
        return summary_from_record(record, actions)


@app.get("/internal/actions", response_model=list[EmailAction])
async def get_actions(
    user_id: str = Query(...),
    status: str = Query(default="open"),
    priority: str | None = Query(default=None),
) -> list[EmailAction]:
    with session_scope() as session:
        stmt = select(ActionRecord).where(
            ActionRecord.user_id == user_id,
            ActionRecord.status == status,
        )
        if priority:
            stmt = stmt.where(ActionRecord.priority == priority)
        stmt = stmt.order_by(desc(ActionRecord.created_at))
        rows = session.execute(stmt).scalars().all()
        return [action_from_record(item) for item in rows]


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


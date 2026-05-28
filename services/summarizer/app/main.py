from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query

from email_core.logging import configure_logging
from email_core.models import ActionType, DailySummary, EmailAction, Priority, ScanResult

from app.settings import settings

app = FastAPI(title="email-summary-summarizer", version="0.1.0")
configure_logging(settings.service_name)

LATEST_SUMMARY: Optional[DailySummary] = None
ACTION_STORE: list[EmailAction] = []


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


@app.post("/internal/process-scan", response_model=DailySummary)
async def process_scan(scan: ScanResult) -> DailySummary:
    global LATEST_SUMMARY, ACTION_STORE

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

    LATEST_SUMMARY = DailySummary(
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
    ACTION_STORE = actions
    return LATEST_SUMMARY


@app.get("/internal/summary/today", response_model=DailySummary)
async def get_today_summary() -> DailySummary:
    if LATEST_SUMMARY:
        return LATEST_SUMMARY

    return DailySummary(
        user_id="demo-user",
        scan_run_id=f"empty-{datetime.utcnow().isoformat()}",
        summary_text="No scan has run yet today.",
        scanned_count=0,
        action_required_count=0,
        urgent_count=0,
        awaiting_reply_count=0,
        top_senders=[],
        actions=[],
    )


@app.get("/internal/actions", response_model=list[EmailAction])
async def get_actions(
    status: str = Query(default="open"),
    priority: Optional[str] = Query(default=None),
) -> list[EmailAction]:
    data = [item for item in ACTION_STORE if item.status == status]
    if priority:
        data = [item for item in data if item.priority.value == priority]
    return data


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


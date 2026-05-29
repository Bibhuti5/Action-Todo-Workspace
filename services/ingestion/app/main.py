from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException

from email_core.logging import configure_logging
from email_core.models import CreateNotificationRequest, DailySummary, ScanRequest, ScanResult

from app.graph_client import MicrosoftGraphMailClient
from app.settings import settings

graph_client = MicrosoftGraphMailClient()


async def fetch_user_access_token(client: httpx.AsyncClient, user_id: str) -> str:
    response = await client.get(f"{settings.auth_url}/internal/tokens/{user_id}")
    if response.status_code == 404:
        raise HTTPException(
            status_code=412,
            detail="mail_not_connected: connect Microsoft 365 account first",
        )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get("access_token", "")
    if not access_token:
        raise HTTPException(status_code=500, detail="missing_access_token")
    return access_token


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)
    app.state.http_client = httpx.AsyncClient(timeout=20)
    yield
    await app.state.http_client.aclose()


app = FastAPI(title="email-summary-ingestion", version="0.1.0", lifespan=lifespan)


@app.post("/internal/scan")
async def run_scan(scan_request: ScanRequest) -> dict:
    client: httpx.AsyncClient = app.state.http_client  # type: ignore[attr-defined]
    scan_run_id = str(uuid4())
    access_token = await fetch_user_access_token(client, scan_request.user_id)
    messages = await graph_client.fetch_recent_messages(
        delegated_access_token=access_token,
        limit=25,
        allow_sample_fallback=settings.allow_sample_mail,
    )

    scan_result = ScanResult(
        user_id=scan_request.user_id,
        scan_run_id=scan_run_id,
        scanned_at=datetime.now(timezone.utc),
        emails=messages,
    )

    summary_response = await client.post(
        f"{settings.summarizer_url}/internal/process-scan",
        json=scan_result.model_dump(mode="json"),
    )
    summary_response.raise_for_status()
    summary = DailySummary.model_validate(summary_response.json())

    if summary.action_required_count > 0:
        note = CreateNotificationRequest(
            user_id=scan_request.user_id,
            title=f"{summary.action_required_count} emails need action",
            body="Open dashboard action table to review priority items.",
            related_email_id=summary.actions[0].email_id if summary.actions else None,
        )
        notification_response = await client.post(
            f"{settings.notifier_url}/internal/notifications",
            json=note.model_dump(mode="json"),
        )
        notification_response.raise_for_status()

    return {
        "status": "completed",
        "scan_run_id": scan_run_id,
        "scanned_count": len(messages),
        "action_required_count": summary.action_required_count,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}

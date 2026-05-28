from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from fastapi import FastAPI

from email_core.logging import configure_logging
from email_core.models import CreateNotificationRequest, DailySummary, ScanRequest, ScanResult

from app.graph_client import MicrosoftGraphMailClient
from app.settings import settings

graph_client = MicrosoftGraphMailClient()


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
    messages = await graph_client.fetch_recent_messages(limit=25)

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
        await client.post(
            f"{settings.notifier_url}/internal/notifications",
            json=note.model_dump(mode="json"),
        )

    return {
        "status": "completed",
        "scan_run_id": scan_run_id,
        "scanned_count": len(messages),
        "action_required_count": summary.action_required_count,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}


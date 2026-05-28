from datetime import datetime

from fastapi import APIRouter, Depends
from httpx import AsyncClient, HTTPError

from email_core.models import DailySummary

from app.deps import get_http_client
from app.settings import settings

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/today", response_model=DailySummary)
async def get_today_dashboard(client: AsyncClient = Depends(get_http_client)) -> DailySummary:
    url = f"{settings.summarizer_url}/internal/summary/today"
    try:
        response = await client.get(url)
        response.raise_for_status()
        return DailySummary.model_validate(response.json())
    except HTTPError:
        # Safe fallback so frontend remains usable before dependencies are fully wired.
        now = datetime.utcnow().isoformat()
        return DailySummary(
            user_id="demo-user",
            scan_run_id=f"fallback-{now}",
            summary_text="No summary available yet. Run a scan to generate daily digest.",
            scanned_count=0,
            action_required_count=0,
            urgent_count=0,
            awaiting_reply_count=0,
            top_senders=[],
            actions=[],
        )


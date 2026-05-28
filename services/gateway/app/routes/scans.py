from datetime import datetime

from fastapi import APIRouter, Depends
from httpx import AsyncClient

from email_core.models import ScanRequest

from app.deps import get_http_client
from app.settings import settings

router = APIRouter(tags=["scans"])


@router.post("/api/scans/run-now")
async def run_scan_now(
    request: ScanRequest,
    client: AsyncClient = Depends(get_http_client),
) -> dict:
    scheduled_for = request.scheduled_for or datetime.utcnow()
    payload = {
        "user_id": request.user_id,
        "run_type": "manual",
        "scheduled_for": scheduled_for.isoformat(),
    }
    response = await client.post(f"{settings.ingestion_url}/internal/scan", json=payload)
    response.raise_for_status()
    return response.json()


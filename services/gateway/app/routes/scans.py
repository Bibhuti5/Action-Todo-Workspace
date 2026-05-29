from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from httpx import AsyncClient

from email_core.models import ScanRequest

from app.deps import get_http_client, get_user_id
from app.settings import settings

router = APIRouter(tags=["scans"])


@router.post("/api/scans/run-now")
async def run_scan_now(
    request: ScanRequest,
    user_id: str = Depends(get_user_id),
    client: AsyncClient = Depends(get_http_client),
) -> dict:
    if request.user_id != user_id:
        raise HTTPException(status_code=403, detail="user_id mismatch")

    scheduled_for = request.scheduled_for or datetime.now(timezone.utc)
    payload = {
        "user_id": request.user_id,
        "run_type": request.run_type,
        "scheduled_for": scheduled_for.isoformat(),
    }
    response = await client.post(f"{settings.ingestion_url}/internal/scan", json=payload)
    response.raise_for_status()
    return response.json()

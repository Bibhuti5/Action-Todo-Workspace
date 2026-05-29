from contextlib import asynccontextmanager
from datetime import datetime
import logging
import asyncio
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from email_core.logging import configure_logging
from email_core.models import ScanRequest

from app.settings import settings

scheduler = AsyncIOScheduler(timezone=settings.app_timezone)
logger = logging.getLogger(__name__)


async def trigger_scan(source: str) -> None:
    payload = ScanRequest(
        user_id=settings.scan_user_id,
        run_type=source,
        scheduled_for=datetime.now(tz=ZoneInfo(settings.app_timezone)),
    ).model_dump(mode="json")

    headers = {"X-User-Id": settings.scan_user_id}
    delays = (1, 2, 4)
    last_error: Exception | None = None
    for delay in delays:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    f"{settings.gateway_url}/api/scans/run-now",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            logger.exception("scheduler_trigger_failed source=%s retry_in=%s", source, delay)
            await asyncio.sleep(delay)
    if last_error:
        raise last_error


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)

    scheduler.add_job(trigger_scan, "cron", hour=11, minute=0, args=["scheduled_11am"])
    scheduler.add_job(trigger_scan, "cron", hour=17, minute=0, args=["scheduled_5pm"])
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="email-summary-scheduler", version="0.1.0", lifespan=lifespan)


@app.post("/internal/trigger-now")
async def trigger_now() -> dict:
    await trigger_scan("manual_scheduler")
    return {"status": "queued", "source": "manual_scheduler"}


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": settings.service_name,
        "timezone": settings.app_timezone,
        "jobs": ["11:00", "17:00"],
    }

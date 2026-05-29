from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from email_core.logging import configure_logging

from app.routes.actions import router as actions_router
from app.routes.dashboard import router as dashboard_router
from app.routes.mail import router as mail_router
from app.routes.notifications import router as notifications_router
from app.routes.scans import router as scans_router
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)
    app.state.http_client = httpx.AsyncClient(timeout=settings.timeout_seconds)
    yield
    await app.state.http_client.aclose()


app = FastAPI(
    title="email-summary-gateway",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(dashboard_router)
app.include_router(actions_router)
app.include_router(notifications_router)
app.include_router(scans_router)
app.include_router(mail_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from email_core.logging import configure_logging
from email_core.storage import MailTokenRecord, init_db, session_scope

from app.settings import settings


class CodeExchangeRequest(BaseModel):
    user_id: str
    code: str


class ManualTokenUpsertRequest(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str | None = None
    scope: str | None = None
    token_type: str | None = None
    expires_in: int | None = None


def token_endpoint() -> str:
    return f"https://login.microsoftonline.com/{settings.ms_tenant_id}/oauth2/v2.0/token"


def expires_at_from_seconds(expires_in: Any) -> datetime | None:
    if expires_in is None:
        return None
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def upsert_token(user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    with session_scope() as session:
        record = session.get(MailTokenRecord, user_id)
        if record is None:
            record = MailTokenRecord(
                user_id=user_id,
                provider="microsoft365",
                access_token=payload["access_token"],
                refresh_token=payload.get("refresh_token"),
                scope=payload.get("scope"),
                token_type=payload.get("token_type"),
                expires_at=expires_at_from_seconds(payload.get("expires_in")),
            )
            session.add(record)
        else:
            record.access_token = payload["access_token"]
            record.refresh_token = payload.get("refresh_token", record.refresh_token)
            record.scope = payload.get("scope", record.scope)
            record.token_type = payload.get("token_type", record.token_type)
            record.expires_at = expires_at_from_seconds(payload.get("expires_in"))
            record.updated_at = datetime.now(timezone.utc)
        session.flush()
        expires_at = ensure_utc(record.expires_at)
        return {
            "user_id": record.user_id,
            "provider": record.provider,
            "access_token": record.access_token,
            "refresh_token": record.refresh_token,
            "scope": record.scope,
            "token_type": record.token_type,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }


async def request_token(form_data: dict[str, str]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(token_endpoint(), data=form_data)
        response.raise_for_status()
        return response.json()


async def refresh_if_needed(record: MailTokenRecord) -> MailTokenRecord:
    expires_at = ensure_utc(record.expires_at)
    if expires_at is None or expires_at > datetime.now(timezone.utc):
        return record
    if not record.refresh_token:
        raise HTTPException(status_code=401, detail="token_expired_reconnect_required")

    token_response = await request_token(
        {
            "client_id": settings.ms_client_id,
            "client_secret": settings.ms_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": record.refresh_token,
            "redirect_uri": settings.ms_redirect_uri,
            "scope": settings.ms_graph_scope,
        }
    )
    upsert_token(record.user_id, token_response)
    with session_scope() as session:
        refreshed = session.get(MailTokenRecord, record.user_id)
        if refreshed is None:
            raise HTTPException(status_code=500, detail="token_refresh_failed")
        return refreshed


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name)
    init_db()
    yield


app = FastAPI(title="email-summary-auth", version="0.1.0", lifespan=lifespan)


@app.post("/internal/oauth/exchange-code")
async def exchange_code(request: CodeExchangeRequest) -> dict:
    if not settings.ms_client_id or not settings.ms_client_secret:
        raise HTTPException(status_code=500, detail="missing_microsoft_client_credentials")

    token_response = await request_token(
        {
            "client_id": settings.ms_client_id,
            "client_secret": settings.ms_client_secret,
            "grant_type": "authorization_code",
            "code": request.code,
            "redirect_uri": settings.ms_redirect_uri,
            "scope": settings.ms_graph_scope,
        }
    )
    return upsert_token(request.user_id, token_response)


@app.post("/internal/tokens")
async def upsert_manual_token(request: ManualTokenUpsertRequest) -> dict:
    payload = request.model_dump()
    payload["expires_in"] = request.expires_in
    return upsert_token(request.user_id, payload)


@app.get("/internal/tokens/{user_id}")
async def get_token(user_id: str) -> dict:
    with session_scope() as session:
        record = session.get(MailTokenRecord, user_id)
        if record is None:
            raise HTTPException(status_code=404, detail="mail_token_not_found")

    refreshed = await refresh_if_needed(record)
    expires_at = ensure_utc(refreshed.expires_at)
    return {
        "user_id": refreshed.user_id,
        "provider": refreshed.provider,
        "access_token": refreshed.access_token,
        "refresh_token": refreshed.refresh_token,
        "scope": refreshed.scope,
        "token_type": refreshed.token_type,
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.service_name}

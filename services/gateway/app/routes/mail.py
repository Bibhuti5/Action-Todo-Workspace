from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from httpx import AsyncClient, HTTPError

from app.deps import get_http_client, get_user_id
from app.settings import settings

router = APIRouter(tags=["mail"])


@router.get("/api/mail/connect/microsoft365")
async def start_microsoft_mail_connect(
    user_id: str = Depends(get_user_id),
) -> dict:
    if not settings.ms_client_id:
        raise HTTPException(status_code=500, detail="missing_ms_client_id")

    query = urlencode(
        {
            "client_id": settings.ms_client_id,
            "response_type": "code",
            "redirect_uri": settings.ms_redirect_uri,
            "response_mode": "query",
            "scope": settings.ms_graph_scope,
            "state": user_id,
        }
    )
    auth_url = (
        f"https://login.microsoftonline.com/{settings.ms_tenant_id}/oauth2/v2.0/authorize"
        f"?{query}"
    )
    return {"provider": "microsoft365", "authorization_url": auth_url}


@router.get("/api/mail/oauth/callback")
async def microsoft_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    client: AsyncClient = Depends(get_http_client),
) -> dict:
    if error:
        raise HTTPException(status_code=400, detail=f"{error}: {error_description}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="missing_code_or_state")

    user_id = state.strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="invalid_state")

    try:
        response = await client.post(
            f"{settings.auth_url}/internal/oauth/exchange-code",
            json={"user_id": user_id, "code": code},
        )
        response.raise_for_status()
    except HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"oauth_exchange_failed: {exc}") from exc
    return {"status": "connected", "user_id": user_id, "provider": "microsoft365"}

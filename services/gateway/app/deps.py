from fastapi import Header, HTTPException, Request
from httpx import AsyncClient


def get_http_client(request: Request) -> AsyncClient:
    return request.app.state.http_client  # type: ignore[attr-defined]


def get_user_id(x_user_id: str = Header(default="")) -> str:
    user_id = x_user_id.strip()
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Missing X-User-Id header. Provide authenticated user context.",
        )
    return user_id

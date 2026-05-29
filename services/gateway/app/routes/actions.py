from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from httpx import AsyncClient, HTTPError

from email_core.models import EmailAction

from app.deps import get_http_client, get_user_id
from app.settings import settings

router = APIRouter(tags=["actions"])


@router.get("/api/actions", response_model=List[EmailAction])
async def get_actions(
    status: str = Query(default="open"),
    priority: Optional[str] = Query(default=None),
    user_id: str = Depends(get_user_id),
    client: AsyncClient = Depends(get_http_client),
) -> List[EmailAction]:
    url = f"{settings.summarizer_url}/internal/actions"
    try:
        response = await client.get(
            url, params={"status": status, "priority": priority, "user_id": user_id}
        )
        response.raise_for_status()
        return [EmailAction.model_validate(item) for item in response.json()]
    except HTTPError:
        return []

from typing import List

from fastapi import APIRouter, Depends, Query
from httpx import AsyncClient, HTTPError

from email_core.models import NotificationItem

from app.deps import get_http_client, get_user_id
from app.settings import settings

router = APIRouter(tags=["notifications"])


@router.get("/api/notifications", response_model=List[NotificationItem])
async def get_notifications(
    status: str = Query(default="unread"),
    user_id: str = Depends(get_user_id),
    client: AsyncClient = Depends(get_http_client),
) -> List[NotificationItem]:
    url = f"{settings.notifier_url}/internal/notifications"
    try:
        response = await client.get(url, params={"status": status, "user_id": user_id})
        response.raise_for_status()
        return [NotificationItem.model_validate(item) for item in response.json()]
    except HTTPError:
        return []


@router.post("/api/notifications/{notification_id}/read", response_model=NotificationItem)
async def mark_notification_read(
    notification_id: str,
    user_id: str = Depends(get_user_id),
    client: AsyncClient = Depends(get_http_client),
) -> NotificationItem:
    url = f"{settings.notifier_url}/internal/notifications/{notification_id}/read"
    response = await client.post(url, params={"user_id": user_id})
    response.raise_for_status()
    return NotificationItem.model_validate(response.json())

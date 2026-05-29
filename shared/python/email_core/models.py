from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    urgent_action = "urgent_action"
    needs_reply = "needs_reply"
    fyi = "fyi"
    low_priority = "low_priority"


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EmailMessage(BaseModel):
    provider_message_id: str
    thread_id: Optional[str] = None
    sender: str
    subject: str
    snippet: str
    received_at: datetime


class EmailAction(BaseModel):
    email_id: str
    subject: str
    sender: str
    action_type: ActionType
    priority: Priority
    confidence: float = Field(ge=0.0, le=1.0)
    due_hint: Optional[str] = None
    status: str = "open"


class ScanRequest(BaseModel):
    user_id: str = "demo-user"
    run_type: str = "manual"
    scheduled_for: Optional[datetime] = None


class ScanResult(BaseModel):
    user_id: str
    scan_run_id: str
    scanned_at: datetime
    emails: List[EmailMessage]


class DailySummary(BaseModel):
    user_id: str
    scan_run_id: str
    summary_text: str
    scanned_count: int
    action_required_count: int
    urgent_count: int
    awaiting_reply_count: int
    top_senders: List[str] = Field(default_factory=list)
    actions: List[EmailAction] = Field(default_factory=list)


class NotificationItem(BaseModel):
    id: str
    user_id: str
    type: str = "action_required"
    title: str
    body: str
    related_email_id: Optional[str] = None
    is_read: bool = False
    created_at: datetime


class CreateNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    related_email_id: Optional[str] = None


class OAuthTokenPayload(BaseModel):
    user_id: str
    provider: str = "microsoft365"
    access_token: str
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    scope: Optional[str] = None
    expires_in: Optional[int] = None

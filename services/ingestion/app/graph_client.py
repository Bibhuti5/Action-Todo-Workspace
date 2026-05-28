from datetime import datetime, timedelta, timezone
from typing import List

import httpx

from email_core.models import EmailMessage


class MicrosoftGraphMailClient:
    """Lightweight graph client wrapper.

    In MVP scaffold mode, if no delegated token is supplied, it returns sample
    messages so service-to-service flow can be tested immediately.
    """

    async def fetch_recent_messages(
        self,
        delegated_access_token: str | None = None,
        limit: int = 20,
    ) -> List[EmailMessage]:
        if not delegated_access_token:
            now = datetime.now(timezone.utc)
            return [
                EmailMessage(
                    provider_message_id="sample-1",
                    sender="manager@company.com",
                    subject="Need approval for Q3 budget revision",
                    snippet="Can you review and approve before EOD?",
                    received_at=now - timedelta(minutes=10),
                ),
                EmailMessage(
                    provider_message_id="sample-2",
                    sender="noreply@tool.io",
                    subject="Weekly report is ready",
                    snippet="Your analytics report is now available.",
                    received_at=now - timedelta(hours=2),
                ),
                EmailMessage(
                    provider_message_id="sample-3",
                    sender="client@partner.org",
                    subject="Action required: contract comments",
                    snippet="Please respond on clauses 4 and 7 today.",
                    received_at=now - timedelta(hours=3),
                ),
            ]

        headers = {"Authorization": f"Bearer {delegated_access_token}"}
        params = {
            "$top": str(limit),
            "$orderby": "receivedDateTime desc",
            "$select": "id,conversationId,from,subject,bodyPreview,receivedDateTime",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://graph.microsoft.com/v1.0/me/messages",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

        messages = []
        for item in payload.get("value", []):
            sender = (
                item.get("from", {})
                .get("emailAddress", {})
                .get("address", "unknown@unknown")
            )
            messages.append(
                EmailMessage(
                    provider_message_id=item["id"],
                    thread_id=item.get("conversationId"),
                    sender=sender,
                    subject=item.get("subject", "(no subject)"),
                    snippet=item.get("bodyPreview", ""),
                    received_at=datetime.fromisoformat(
                        item["receivedDateTime"].replace("Z", "+00:00")
                    ),
                )
            )
        return messages


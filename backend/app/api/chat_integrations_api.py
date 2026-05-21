from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/api/chat-integrations", tags=["chat-integrations"])


class NotificationPayload(BaseModel):
    title: str = ""
    body: str = ""
    platform: str | None = ""


class SendMessagePayload(BaseModel):
    platform: str
    contact: str
    text: str = ""
    media_path: str | None = ""
    voice: bool = False
    approved: bool = False


class QueryPayload(BaseModel):
    platform: str | None = ""
    contact: str | None = ""
    query: str | None = ""
    unread_only: bool = False
    limit: int = 20


def _manager():
    from chat_integrations.manager import get_chat_integration_manager

    return get_chat_integration_manager()


@router.get("/status")
def chat_integrations_status():
    return _manager().status()


@router.post("/notifications/parse")
def parse_notification(payload: NotificationPayload):
    return _manager().ingest_notification(payload.title, payload.body, platform=payload.platform or "")


@router.post("/messages/read")
def read_messages(payload: QueryPayload):
    return _manager().read_messages(platform=payload.platform or "", contact=payload.contact or "", unread_only=payload.unread_only, limit=payload.limit)


@router.post("/messages/send")
def send_message(payload: SendMessagePayload):
    return _manager().send_message(
        platform=payload.platform,
        contact=payload.contact,
        text=payload.text,
        media_path=payload.media_path or "",
        voice=payload.voice,
        approved=payload.approved,
    )


@router.post("/messages/summarize-unread")
def summarize_unread(payload: QueryPayload):
    return _manager().summarize_unread(platform=payload.platform or "")


@router.post("/smart-replies")
def smart_replies(payload: QueryPayload):
    return _manager().suggest_replies(platform=payload.platform or "", contact=payload.contact or "")


@router.post("/contacts/search")
def search_contacts(payload: QueryPayload):
    return _manager().search_contacts(payload.query or "", platform=payload.platform or "")


@router.post("/threads/mute")
def mute_thread(payload: QueryPayload):
    return _manager().mute_thread(platform=payload.platform or "", thread=payload.contact or payload.query or "", approved=False)

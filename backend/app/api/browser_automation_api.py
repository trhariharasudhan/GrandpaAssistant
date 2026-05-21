from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


router = APIRouter(prefix="/api/browser", tags=["browser-automation"])


class BrowserAutomationRequest(BaseModel):
    request: str
    url: str | None = None
    browser: str | None = "chrome"
    session_id: str | None = None
    confirmed: bool = False


def _service():
    from browser_automation.service import get_browser_automation_service

    return get_browser_automation_service()


@router.get("/status")
def browser_status():
    return _service().status()


@router.post("/plan")
def browser_plan(request: BrowserAutomationRequest):
    return _service().plan(request.request, url=request.url or "", browser=request.browser or "chrome")


@router.post("/execute")
def browser_execute(request: BrowserAutomationRequest):
    return _service().execute(
        request.request,
        url=request.url or "",
        browser=request.browser or "chrome",
        session_id=request.session_id,
        confirmed=bool(request.confirmed),
    )


@router.post("/stream")
def browser_stream(request: BrowserAutomationRequest):
    from browser_automation.service import sse_events

    events = _service().stream(
        request.request,
        url=request.url or "",
        browser=request.browser or "chrome",
        session_id=request.session_id,
        confirmed=bool(request.confirmed),
    )
    return StreamingResponse(sse_events(events), media_type="text/event-stream")


@router.post("/sessions/{session_id}/close")
def browser_close_session(session_id: str):
    service = _service()
    ok = service.session_manager.close_session(session_id)
    return {"ok": ok, "session_id": session_id}

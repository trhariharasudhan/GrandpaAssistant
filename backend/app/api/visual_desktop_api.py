from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/api/visual-desktop", tags=["visual-desktop"])


class VisualActionPayload(BaseModel):
    request: str
    approved: bool = False


def _service():
    from visual_desktop.service import get_visual_desktop_service

    return get_visual_desktop_service()


@router.get("/status")
def visual_status():
    return _service().status()


@router.post("/analyze")
def analyze_screen():
    return _service().analyze_screen(include_image=False)


@router.post("/plan-action")
def plan_visual_action(payload: VisualActionPayload):
    return _service().plan_action(payload.request, approved=payload.approved)

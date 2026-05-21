from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/api/local-actions", tags=["local-action-orchestrator"])


class LocalActionCommand(BaseModel):
    command: str


def _orchestrator():
    from local_action_orchestrator.orchestrator import get_local_action_orchestrator

    return get_local_action_orchestrator()


@router.post("/classify")
def classify_local_action(payload: LocalActionCommand):
    return _orchestrator().classify(payload.command)


@router.post("/plan")
def plan_local_action(payload: LocalActionCommand):
    return _orchestrator().plan(payload.command)

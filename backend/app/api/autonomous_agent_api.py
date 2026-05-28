from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


router = APIRouter(prefix="/api/agent", tags=["autonomous-agent"])


class GoalPayload(BaseModel):
    goal: str
    approved: bool = False


class TaskPayload(BaseModel):
    task_id: str
    approved: bool = False


class ExecutePayload(BaseModel):
    plan_id: str | None = None
    plan_payload: dict | None = None
    confirmed: bool = False
    confirmation_token: str | None = None


def _manager():
    from autonomous_agent.manager import get_autonomous_agent_manager

    return get_autonomous_agent_manager()


def _agent_v1():
    from core.autonomous_agent import AgentExecutorBridge, AgentStateStore, create_plan

    return create_plan, AgentStateStore(), AgentExecutorBridge()


def _sse(events):
    for event in events:
        yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"


@router.get("/status")
def agent_status():
    return _manager().status()


@router.post("/plan")
def plan_goal(payload: GoalPayload):
    legacy = _manager().plan_goal(payload.goal)
    create_plan, state_store, _bridge = _agent_v1()
    v1_plan = create_plan(payload.goal)
    v1_payload = state_store.save_plan(v1_plan)
    return {**legacy, **v1_payload}


@router.post("/execute")
def execute_plan(payload: ExecutePayload):
    _create_plan, _state_store, bridge = _agent_v1()
    return bridge.execute(
        plan_id=payload.plan_id or "",
        plan_payload=payload.plan_payload,
        confirmed=bool(payload.confirmed),
        confirmation_token=payload.confirmation_token or "",
    )


@router.post("/tasks/step")
def run_task_step(payload: TaskPayload):
    return _manager().run_next_step(payload.task_id, approved=payload.approved)


@router.post("/stream")
def stream_goal(payload: GoalPayload):
    return StreamingResponse(_sse(_manager().stream_goal(payload.goal, approved=payload.approved)), media_type="text/event-stream")

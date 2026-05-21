from __future__ import annotations

import time
from typing import Any, Iterable

from .executor import ExecutorManager
from .planner import GoalPlanner, TaskGraphEngine
from .state import ContextManager, compact_text


class AutonomousAgentManager:
    def __init__(
        self,
        *,
        planner: GoalPlanner | None = None,
        graph_engine: TaskGraphEngine | None = None,
        executor: ExecutorManager | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:
        self.planner = planner or GoalPlanner()
        self.graph_engine = graph_engine or TaskGraphEngine()
        self.executor = executor or ExecutorManager()
        self.context_manager = context_manager or ContextManager()

    def plan_goal(self, goal: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
        plan = self.planner.decompose_goal(goal, context=context)
        graph = self.graph_engine.build_graph(plan)
        task = self.context_manager.create_task(goal, graph)
        return {"ok": True, "task": task, "plan": plan, "graph": graph}

    def run_next_step(self, task_id: str, *, approved: bool = False) -> dict[str, Any]:
        payload = self.context_manager.load()
        task = next((item for item in payload.get("tasks", []) if item.get("task_id") == task_id), None)
        if not task:
            return {"ok": False, "message": "Task not found.", "task_id": compact_text(task_id)}
        nodes = ((task.get("graph") or {}).get("nodes") or [])
        node = next((item for item in nodes if item.get("status") == "pending"), None)
        if not node:
            self.context_manager.update_task(task_id, status="done")
            return {"ok": True, "message": "Task already complete.", "task_id": task_id, "status": "done"}
        result = self.executor.execute_node(node, approved=approved)
        node["status"] = result.get("status") or ("done" if result.get("ok") else "failed")
        history = task.setdefault("action_history", [])
        history.append({"node_id": node.get("node_id"), "status": node["status"], "at": time.time(), "message": compact_text(result.get("message"))})
        status = "running"
        if node["status"] in {"waiting_for_approval", "waiting_for_user", "waiting_for_details"}:
            status = node["status"]
        elif all(item.get("status") != "pending" for item in nodes):
            status = "done"
        self.context_manager.update_task(task_id, graph=task.get("graph"), action_history=history, status=status)
        return {"ok": bool(result.get("ok")), "task_id": task_id, "node": node, "result": result, "status": status}

    def stream_goal(self, goal: str, *, approved: bool = False) -> Iterable[dict[str, Any]]:
        planned = self.plan_goal(goal)
        yield {"type": "planned", "task_id": planned["task"]["task_id"], "graph": planned["graph"]}
        result = self.run_next_step(planned["task"]["task_id"], approved=approved)
        yield {"type": "step", "result": result}
        if result.get("status") in {"waiting_for_approval", "waiting_for_user", "waiting_for_details"}:
            yield {"type": "paused", "reason": result.get("status")}
        else:
            yield {"type": "done", "task_id": planned["task"]["task_id"]}

    def status(self) -> dict[str, Any]:
        return {"ok": True, "state": self.context_manager.status(), "planner": "deterministic_goal_planner", "async_ready": True, "human_in_loop": True}


_GLOBAL_MANAGER: AutonomousAgentManager | None = None


def get_autonomous_agent_manager() -> AutonomousAgentManager:
    global _GLOBAL_MANAGER
    if _GLOBAL_MANAGER is None:
        _GLOBAL_MANAGER = AutonomousAgentManager()
    return _GLOBAL_MANAGER

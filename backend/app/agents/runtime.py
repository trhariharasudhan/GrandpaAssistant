from __future__ import annotations

import threading
import time
from typing import Any

from agents.catalog import build_default_agents
from agents.message_bus import AgentMessageBus
from agents.state_store import AgentStateStore
from cognition.proactive_engine import maybe_generate_idle_nudge


def _detect_context(text: str, emotion: str) -> str:
    lowered = " ".join(str(text or "").lower().split())
    if emotion in {"sad", "angry"}:
        return "emotional"
    work_tokens = ("project", "code", "bug", "meeting", "email", "deadline", "task", "deploy", "server")
    if any(token in lowered for token in work_tokens):
        return "work"
    return "casual"


def _goal_steps(goal_text: str) -> list[str]:
    title = " ".join(str(goal_text or "").split()).strip()
    if not title:
        return []
    return [
        f"Clarify the exact outcome for {title}.",
        f"Break {title} into 3 to 5 concrete tasks.",
        f"Complete the highest-impact task first.",
        f"Review progress and adjust the next step.",
    ]


class AssistantRuntime:
    def __init__(self):
        self.bus = AgentMessageBus()
        self.state = AgentStateStore()
        self.agents = {}
        self._running = False
        self._loop_thread = None
        self._refresh_interval_seconds = 20.0
        self._register_default_agents()

    def _register_default_agents(self) -> None:
        for agent in build_default_agents():
            agent.attach_runtime(self)
            self.agents[agent.agent_id] = agent
            self.bus.subscribe("assistant.*", agent.handle_event, owner=agent.agent_id)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self.state.mark_started()
        self.bus.publish("assistant.runtime.started", {"agent_count": len(self.agents)}, source="runtime")
        self._loop_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._loop_thread.start()

    def stop(self) -> None:
        self._running = False
        self.bus.publish("assistant.runtime.stopped", {}, source="runtime")

    def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                self.refresh_all()
                snapshot = self.status_payload()
                if snapshot["runtime"].get("autonomous_mode", True):
                    self.bus.publish("assistant.heartbeat", {"autonomous_mode": True}, source="runtime")
                    proactive = maybe_generate_idle_nudge(snapshot)
                    if proactive:
                        self.bus.publish("assistant.proactive.suggestion", proactive, source="intelligence-agent")
            except Exception:
                pass
            time.sleep(self._refresh_interval_seconds)

    def refresh_all(self) -> dict[str, Any]:
        snapshot = {}
        for agent in self.agents.values():
            try:
                status = agent.summary()
            except Exception as error:
                status = {
                    "name": agent.name,
                    "description": agent.description,
                    "capabilities": list(agent.capabilities),
                    "ready": False,
                    "error": str(error),
                }
            self.state.update_agent(agent.agent_id, status)
            if agent.agent_id == "plugin-manager":
                self.state.replace_plugins(status.get("plugins", {}))
            snapshot[agent.agent_id] = status
        return snapshot

    def observe_user_message(self, text: str, *, source: str = "chat", emotion: dict | None = None, mood: dict | None = None) -> dict[str, Any]:
        emotion_name = str((emotion or {}).get("emotion", "neutral")).strip() or "neutral"
        mood_name = str((mood or {}).get("last_mood", emotion_name)).strip() or emotion_name
        context = _detect_context(text, emotion_name)
        self.state.set_runtime_mode(current_context=context)
        self.state.record_user_message(text, emotion=emotion_name, mood=mood_name, source=source)
        event = self.bus.publish(
            "assistant.user_message",
            {
                "text": text,
                "source": source,
                "emotion": emotion or {},
                "mood": mood or {},
                "context": context,
            },
            source=source,
        )
        return {
            "context": context,
            "event": event,
        }

    def observe_assistant_reply(self, text: str, *, source: str = "assistant") -> dict[str, Any]:
        self.state.record_assistant_reply(text, source=source)
        event = self.bus.publish(
            "assistant.reply",
            {"text": text, "source": source},
            source=source,
        )
        return {"event": event}

    def set_thinking_mode(self, mode: str) -> dict[str, Any]:
        normalized = str(mode or "adaptive").strip().lower() or "adaptive"
        if normalized not in {"adaptive", "fast", "deep"}:
            normalized = "adaptive"
        self.state.set_runtime_mode(thinking_mode=normalized)
        self.bus.publish("assistant.mode.changed", {"thinking_mode": normalized}, source="runtime")
        return self.status_payload()

    def set_autonomous_mode(self, enabled: bool) -> dict[str, Any]:
        self.state.set_runtime_mode(autonomous_mode=bool(enabled))
        self.bus.publish("assistant.mode.changed", {"autonomous_mode": bool(enabled)}, source="runtime")
        return self.status_payload()

    def create_goal(self, title: str, steps: list[str] | None = None, *, source: str = "user") -> dict[str, Any]:
        goal = self.state.add_goal(title, steps or _goal_steps(title), source=source)
        self.bus.publish("assistant.goal.created", {"goal": goal}, source=source)
        return goal

    def goals(self) -> list[dict[str, Any]]:
        return list(self.state.snapshot().get("goals", []))

    def agent_statuses(self) -> dict[str, Any]:
        return self.state.snapshot().get("agents", {})

    def recent_bus_events(self, limit: int = 30) -> list[dict[str, Any]]:
        return self.bus.recent_events(limit=limit)

    def status_payload(self) -> dict[str, Any]:
        snapshot = self.state.snapshot()
        return {
            "running": self._running,
            "runtime": snapshot.get("runtime", {}),
            "conversation": snapshot.get("conversation", {}),
            "goals": snapshot.get("goals", []),
            "plugins": snapshot.get("plugins", {}),
            "agents": snapshot.get("agents", {}),
            "bus": self.bus.stats(),
        }


ASSISTANT_RUNTIME = AssistantRuntime()

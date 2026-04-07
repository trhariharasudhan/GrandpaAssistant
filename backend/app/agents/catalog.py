from __future__ import annotations

import importlib.util
from typing import Any

from agents.base import BaseAgent
from cognition.hub import intelligence_status_payload
from cognition.learning_engine import learning_status_payload
from device_manager import DEVICE_MANAGER
from security.auth_manager import auth_status_payload
from security.hub import security_status_payload
from features.voice.listen import (
    clap_wake_status_summary,
    continuous_conversation_enabled,
    current_voice_mode,
    stt_backend_payload,
)
from features.voice.speak import tts_backend_payload
from features.vision.object_detection import (
    get_object_detection_model_name,
    get_watch_status,
    is_object_detection_available,
    object_detection_import_error,
)
from features.security.face_verification import is_face_enrolled
from modules.task_module import get_planner_focus_snapshot, get_task_data
from modules.nextgen_module import nextgen_status_snapshot
from plugin_system import plugin_status_payload
from shared.offline_multi_model import MODEL_BY_MODE, get_ollama_status
from brain.semantic_memory import semantic_memory_status
from utils.config import get_setting
from utils.emotion import analyze_emotion
from utils.mood_memory import mood_status_payload


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _ocr_status() -> dict[str, Any]:
    return {
        "opencv": _module_available("cv2"),
        "tesseract": _module_available("pytesseract"),
    }


def _face_security_status() -> dict[str, Any]:
    return {
        "module_available": _module_available("features.security.face_verification") or _module_available("security.face_verification"),
        "face_enrolled": bool(is_face_enrolled()),
    }


class BrainAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        learning = learning_status_payload()
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            "thinking_mode": self.runtime.state.snapshot()["runtime"].get("thinking_mode", "adaptive") if self.runtime else "adaptive",
            "routing_models": dict(MODEL_BY_MODE),
            "ollama": get_ollama_status(),
            "prompt_optimization": learning.get("prompt_optimization", {}),
            "learned_preferences": learning.get("user_preferences", {}),
        }


class VoiceAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            "wake_word": str(get_setting("wake_word", "hey grandpa") or "hey grandpa"),
            "voice_mode": current_voice_mode(),
            "continuous_conversation": bool(continuous_conversation_enabled()),
            "wake_clap": clap_wake_status_summary(),
            "stt": stt_backend_payload(),
            "tts": tts_backend_payload(),
            "auth": auth_status_payload(),
        }


class VisionAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            "ocr": _ocr_status(),
            "object_detection": {
                "available": bool(is_object_detection_available()),
                "model": get_object_detection_model_name(),
                "watch": get_watch_status(),
                "error": object_detection_import_error(),
            },
            "face_security": _face_security_status(),
        }


class TaskAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        learning = learning_status_payload()
        task_data = get_task_data()
        tasks = task_data.get("tasks", []) if isinstance(task_data, dict) else []
        reminders = task_data.get("reminders", []) if isinstance(task_data, dict) else []
        pending_tasks = [task for task in tasks if not task.get("completed")]
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            "planner": get_planner_focus_snapshot(),
            "nextgen": nextgen_status_snapshot(),
            "pending_task_count": len(pending_tasks),
            "reminder_count": len(reminders),
            "automation_suggestions": learning.get("automation_suggestions", [])[:3],
        }


class MemoryAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        learning = learning_status_payload()
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            "semantic_memory": semantic_memory_status(prewarm=False),
            "mood_memory": mood_status_payload(),
            "response_memory": learning.get("response_memory", {}),
            "behavior_learning": learning.get("behavior_learning", {}),
        }


class EmotionAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            "latest_mood": mood_status_payload(),
        }

    def handle_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        if event.get("topic") != "assistant.user_message":
            return None
        text = str((event.get("payload") or {}).get("text", "")).strip()
        if not text:
            return None
        analysis = analyze_emotion(text)
        return {
            "emotion": analysis.get("emotion", "neutral"),
            "compound": analysis.get("compound", 0.0),
        }


class PluginManagerAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        payload = plugin_status_payload()
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            "plugins": payload,
        }


class IntelligenceAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        runtime_snapshot = self.runtime.status_payload() if self.runtime else {}
        payload = intelligence_status_payload(runtime_snapshot)
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            **payload,
        }


class SecurityAgent(BaseAgent):
    def refresh_status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "ready": True,
            **security_status_payload(DEVICE_MANAGER),
        }


def build_default_agents() -> list[BaseAgent]:
    return [
        BrainAgent("brain-agent", "Brain Agent", "LLM reasoning, routing, and planning.", ["llm-routing", "fast-mode", "deep-mode"]),
        VoiceAgent("voice-agent", "Voice Agent", "Speech input, output, wake word, and interruption control.", ["stt", "tts", "wake-word", "interrupts"]),
        VisionAgent("vision-agent", "Vision Agent", "OCR, object detection, and face-aware capabilities.", ["ocr", "object-detection", "face-security"]),
        TaskAgent("task-agent", "Task Agent", "Tasks, reminders, automation, and system-action coordination.", ["tasks", "reminders", "automation", "system-control"]),
        MemoryAgent("memory-agent", "Memory Agent", "Short-term, semantic, and mood-aware memory state.", ["short-term-memory", "semantic-memory", "mood-memory"]),
        EmotionAgent("emotion-agent", "Emotion Agent", "Emotion detection, mood tracking, and tone adaptation.", ["emotion-detection", "mood-tracking", "tone-adaptation"]),
        IntelligenceAgent("intelligence-agent", "Intelligence Agent", "Learning, insights, decision support, workflow chaining, and proactive intelligence.", ["self-improvement", "insights", "decisions", "workflows", "knowledge-graph", "recovery", "sync"]),
        SecurityAgent("security-agent", "Security Agent", "Authentication, permissions, threat detection, device trust, and data protection.", ["authentication", "authorization", "threat-detection", "device-security", "encryption"]),
        PluginManagerAgent("plugin-manager", "Plugin Manager", "Dynamic plugin discovery and execution registry.", ["plugin-load", "plugin-unload", "plugin-hooks"]),
    ]

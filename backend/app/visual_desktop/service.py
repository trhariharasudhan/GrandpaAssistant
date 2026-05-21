from __future__ import annotations

from typing import Any

from .action_planner import ActionPlanner
from .capture import ScreenCaptureService, compact_text
from .ocr import OCRService
from .reasoning import VisualReasoningEngine
from .safe_executor import SafeActionExecutor
from .ui_detector import UIElementDetector


class VisualDesktopService:
    def __init__(
        self,
        *,
        capture: ScreenCaptureService | None = None,
        ocr: OCRService | None = None,
        detector: UIElementDetector | None = None,
        reasoning: VisualReasoningEngine | None = None,
        planner: ActionPlanner | None = None,
        executor: SafeActionExecutor | None = None,
    ) -> None:
        self.capture_service = capture or ScreenCaptureService()
        self.ocr_service = ocr or OCRService()
        self.detector = detector or UIElementDetector()
        self.reasoning = reasoning or VisualReasoningEngine()
        self.planner = planner or ActionPlanner()
        self.executor = executor or SafeActionExecutor()

    def analyze_screen(self, *, include_image: bool = False) -> dict[str, Any]:
        capture = self.capture_service.capture(include_image=include_image)
        ocr = self.ocr_service.extract_text(capture)
        elements = self.detector.detect(capture=capture, ocr=ocr)
        summary = self.reasoning.summarize(ocr=ocr, elements=elements)
        return {"ok": True, "capture": self._safe_capture(capture), "ocr": self._safe_ocr(ocr), "elements": elements, "summary": summary}

    def plan_action(self, request: str, *, approved: bool = False) -> dict[str, Any]:
        context = self.analyze_screen(include_image=False)
        plan = self.planner.plan(request, visual_context=context)
        result = self.executor.execute(plan, approved=approved)
        return {"ok": bool(result.get("ok")), "request": compact_text(request), "visual_summary": context.get("summary"), "plan": plan, "result": result}

    def status(self) -> dict[str, Any]:
        return {"ok": True, "capture_available": True, "ocr_available": True, "ui_detection": "ocr_heuristic", "real_clicks_enabled": False, "safe_action_executor": True}

    def _safe_capture(self, capture: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in capture.items() if key not in {"image_base64", "screenshot_base64"}}

    def _safe_ocr(self, ocr: dict[str, Any]) -> dict[str, Any]:
        return {"ok": bool(ocr.get("ok")), "summary": compact_text(ocr.get("summary") or ocr.get("text"), 1000), "line_count": len(ocr.get("lines") or []), "message": compact_text(ocr.get("message"))}


_GLOBAL_SERVICE: VisualDesktopService | None = None


def get_visual_desktop_service() -> VisualDesktopService:
    global _GLOBAL_SERVICE
    if _GLOBAL_SERVICE is None:
        _GLOBAL_SERVICE = VisualDesktopService()
    return _GLOBAL_SERVICE

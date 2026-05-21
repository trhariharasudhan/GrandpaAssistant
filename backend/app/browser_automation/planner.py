from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote_plus


def _compact_text(value: Any, limit: int = 2000) -> str:
    text = " ".join(str(value or "").split()).strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class BrowserActionPlanner:
    """Deterministic browser plan builder with safe AI-planning extension points."""

    def build_plan(self, request: str, *, url: str = "", browser: str = "chrome") -> dict[str, Any]:
        goal = _compact_text(request)
        normalized = goal.lower()
        target_url = _compact_text(url)
        steps: list[dict[str, Any]] = []
        intent = "browser_task"
        requires_confirmation = False

        if "youtube" in normalized or "play music" in normalized:
            intent = "play_media"
            query = self._extract_after(normalized, ("play", "search", "youtube")) or "music"
            target_url = "https://www.youtube.com/results?search_query=" + quote_plus(query)
            steps = [
                {"action": "goto", "url": target_url},
                {"action": "click", "selector": "text=Play", "description": "play a suitable media result", "optional": True},
            ]
        elif "linkedin" in normalized:
            intent = "login_or_open_linkedin"
            target_url = "https://www.linkedin.com/"
            requires_confirmation = "login" in normalized or "apply" in normalized
            steps = [{"action": "goto", "url": target_url}, {"action": "read", "target": "page"}]
            if "job" in normalized or "filter" in normalized:
                intent = "apply_job_filters"
                steps.extend(
                    [
                        {"action": "click", "selector": "text=Jobs", "description": "open jobs area", "optional": True},
                        {"action": "fill", "selector": "input[aria-label*=Search]", "value": self._extract_job_query(goal), "optional": True},
                    ]
                )
        elif "cab" in normalized or "taxi" in normalized or "uber" in normalized or "ola" in normalized:
            intent = "book_cab"
            target_url = "https://www.uber.com/"
            requires_confirmation = True
            steps = [{"action": "goto", "url": target_url}, {"action": "read", "target": "page"}]
        elif "order food" in normalized or "swiggy" in normalized or "zomato" in normalized:
            intent = "order_food"
            target_url = "https://www.swiggy.com/"
            requires_confirmation = True
            steps = [{"action": "goto", "url": target_url}, {"action": "read", "target": "page"}]
        elif target_url:
            intent = "open_url"
            steps = [{"action": "goto", "url": target_url}, {"action": "read", "target": "page"}]
        else:
            query = re.sub(r"^(search|google|find)\s+", "", normalized).strip() or goal
            target_url = "https://www.google.com/search?q=" + quote_plus(query)
            intent = "search_web"
            steps = [{"action": "goto", "url": target_url}, {"action": "read", "target": "page"}]

        return {
            "goal": goal,
            "intent": intent,
            "browser": browser,
            "url": target_url,
            "steps": steps,
            "requires_confirmation": requires_confirmation,
            "planner": "deterministic_browser_planner",
        }

    def _extract_after(self, text: str, prefixes: tuple[str, ...]) -> str:
        for prefix in prefixes:
            if prefix in text:
                value = text.split(prefix, 1)[1].strip(" :,-")
                if value:
                    return value
        return ""

    def _extract_job_query(self, text: str) -> str:
        match = re.search(r"(?:for|as)\s+([a-zA-Z0-9 .+#-]+)", text)
        return _compact_text(match.group(1) if match else "software engineer", 120)

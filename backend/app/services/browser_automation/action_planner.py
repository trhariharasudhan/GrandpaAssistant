"""
Action Planner - AI-driven planning for browser automation sequences.

Converts natural language commands into structured action sequences using Ollama.
Integrated with AI learning system for improved action planning.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Any, List

logger = logging.getLogger(__name__)


@dataclass
class ActionStep:
    """Single action step in a plan."""
    step_id: int
    action_type: str  # click, fill, navigate, extract, submit, etc.
    selector: Optional[str] = None  # CSS selector or element identifier
    value: Optional[str] = None  # Value for fill actions
    context: Optional[str] = None  # Human-readable context
    dependencies: list[int] = None  # Step IDs this depends on
    retryable: bool = True
    confidence: float = 0.5  # Confidence score 0-1
    fallback_selector: Optional[str] = None  # Alternative selector if first fails


@dataclass
class ActionPlan:
    """Complete action plan for a command."""
    command: str
    goal: str
    steps: list[ActionStep]
    expected_outcome: str
    fallback_actions: Optional[list[ActionStep]] = None
    plan_confidence: float = 0.5  # Overall confidence for the plan
    alternative_plans: Optional[List['ActionPlan']] = None  # Alternative strategies


class BrowserActionPlanner:
    """
    Plans action sequences using Ollama for intelligent web automation.
    
    Converts natural language commands into structured Playwright action sequences.
    """

    def __init__(self, ollama_client=None, model: str = "neural-chat"):
        self.ollama_client = ollama_client
        self.model = model
        self.plan_cache: dict[str, ActionPlan] = {}
        logger.info(f"BrowserActionPlanner initialized with model={model}")

    async def plan_action_sequence(
        self,
        command: str,
        page_context: str = "",
        existing_url: str = "",
    ) -> Optional[ActionPlan]:
        """
        Generate an action plan from a natural language command.
        
        Args:
            command: Natural language command (e.g., "Book an Uber")
            page_context: Current page content/context
            existing_url: Current page URL
            
        Returns:
            ActionPlan with structured steps or None if planning failed
        """
        # Check cache
        cache_key = f"{command}|{existing_url}"
        if cache_key in self.plan_cache:
            logger.info(f"Using cached plan for: {command}")
            return self.plan_cache[cache_key]

        try:
            # Build prompt for Ollama
            prompt = self._build_planning_prompt(command, page_context, existing_url)
            
            logger.info(f"Generating plan for: {command}")
            
            if self.ollama_client:
                response = await self._call_ollama(prompt)
            else:
                response = self._get_demo_plan(command)
            
            # Parse response into ActionPlan
            plan = self._parse_plan_response(command, response)
            
            if plan:
                self.plan_cache[cache_key] = plan
                logger.info(f"Generated plan with {len(plan.steps)} steps")
            
            return plan

        except Exception as e:
            logger.error(f"Failed to generate action plan: {e}")
            return None

    def _build_planning_prompt(
        self,
        command: str,
        page_context: str,
        current_url: str,
    ) -> str:
        """Build prompt for Ollama action planning."""
        return f"""You are an expert web automation planner. Generate a structured action plan.

Command: {command}
Current URL: {current_url}
Page Context: {page_context[:500]}

Generate a JSON plan with:
{{
  "goal": "what you're trying to accomplish",
  "steps": [
    {{
      "step_id": 1,
      "action_type": "navigate|click|fill|extract|submit",
      "selector": "CSS selector or element identifier",
      "value": "value for fill actions",
      "context": "human-readable description"
    }}
  ],
  "expected_outcome": "what should happen after all steps"
}}

Respond with ONLY valid JSON."""

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama for action planning."""
        try:
            if hasattr(self.ollama_client, 'generate'):
                response = await self.ollama_client.generate(
                    model=self.model,
                    prompt=prompt,
                    stream=False,
                )
                return response.get("response", "")
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
        return ""

    def _get_demo_plan(self, command: str) -> str:
        """Return demo plan for testing (when Ollama not available)."""
        demo_plans = {
            "book.*uber": json.dumps({
                "goal": "Open Uber and search for a ride",
                "steps": [
                    {
                        "step_id": 1,
                        "action_type": "navigate",
                        "value": "https://www.uber.com",
                        "context": "Navigate to Uber website"
                    },
                    {
                        "step_id": 2,
                        "action_type": "click",
                        "selector": "[data-testid='request-ride-button']",
                        "context": "Click request ride button"
                    },
                    {
                        "step_id": 3,
                        "action_type": "fill",
                        "selector": "[data-testid='destination-input']",
                        "value": "{command}",
                        "context": "Enter destination"
                    },
                ],
                "expected_outcome": "Ride request initiated"
            }),
            "order.*food": json.dumps({
                "goal": "Order food from Swiggy",
                "steps": [
                    {
                        "step_id": 1,
                        "action_type": "navigate",
                        "value": "https://www.swiggy.com",
                        "context": "Navigate to Swiggy"
                    },
                    {
                        "step_id": 2,
                        "action_type": "fill",
                        "selector": "[data-testid='location-input']",
                        "value": "",
                        "context": "Enter delivery location"
                    },
                ],
                "expected_outcome": "Food order placed"
            }),
            "play.*music": json.dumps({
                "goal": "Open YouTube and play music",
                "steps": [
                    {
                        "step_id": 1,
                        "action_type": "navigate",
                        "value": "https://www.youtube.com/results?search_query=music",
                        "context": "Navigate to YouTube"
                    },
                    {
                        "step_id": 2,
                        "action_type": "click",
                        "selector": "yt-simple-endpoint[href*='/watch']",
                        "context": "Click first music video"
                    },
                ],
                "expected_outcome": "Music playing"
            }),
        }

        for pattern, plan in demo_plans.items():
            import re
            if re.search(pattern, command.lower()):
                return plan

        return json.dumps({
            "goal": command,
            "steps": [
                {
                    "step_id": 1,
                    "action_type": "navigate",
                    "value": f"https://google.com/search?q={command}",
                    "context": "Search for command"
                }
            ],
            "expected_outcome": "Search completed"
        })

    def _parse_plan_response(self, command: str, response: str) -> Optional[ActionPlan]:
        """Parse Ollama response into ActionPlan."""
        try:
            if not response:
                return None

            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            steps = []
            for step_data in data.get("steps", []):
                step = ActionStep(
                    step_id=step_data.get("step_id", 0),
                    action_type=step_data.get("action_type", ""),
                    selector=step_data.get("selector"),
                    value=step_data.get("value"),
                    context=step_data.get("context"),
                    dependencies=step_data.get("dependencies", []),
                )
                steps.append(step)

            plan = ActionPlan(
                command=command,
                goal=data.get("goal", ""),
                steps=steps,
                expected_outcome=data.get("expected_outcome", ""),
            )

            return plan

        except Exception as e:
            logger.error(f"Failed to parse plan response: {e}")
            return None

    def clear_cache(self):
        """Clear plan cache."""
        self.plan_cache.clear()
        logger.info("Plan cache cleared")

"""
Browser Safety Layer - Confirmation and validation for dangerous actions.

Prevents accidental form submissions, payments, and account modifications
without explicit user confirmation.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ActionRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActionSafetyCheck:
    """Safety check for an action."""
    action_type: str
    risk_level: ActionRiskLevel
    description: str
    requires_confirmation: bool
    dangerous_keywords: list[str]


# Dangerous action patterns
DANGEROUS_ACTIONS = {
    "form_submit": ActionSafetyCheck(
        action_type="form_submit",
        risk_level=ActionRiskLevel.HIGH,
        description="Form submission",
        requires_confirmation=True,
        dangerous_keywords=["checkout", "buy", "pay", "submit", "send", "confirm"],
    ),
    "payment": ActionSafetyCheck(
        action_type="payment",
        risk_level=ActionRiskLevel.CRITICAL,
        description="Payment transaction",
        requires_confirmation=True,
        dangerous_keywords=["payment", "transaction", "credit card", "debit card", "pay now"],
    ),
    "account_modification": ActionSafetyCheck(
        action_type="account_modification",
        risk_level=ActionRiskLevel.HIGH,
        description="Account/profile modification",
        requires_confirmation=True,
        dangerous_keywords=["password", "email", "account", "profile", "settings", "delete account"],
    ),
    "deletion": ActionSafetyCheck(
        action_type="deletion",
        risk_level=ActionRiskLevel.CRITICAL,
        description="Deletion operation",
        requires_confirmation=True,
        dangerous_keywords=["delete", "remove", "clear all", "discard", "trash"],
    ),
    "file_operation": ActionSafetyCheck(
        action_type="file_operation",
        risk_level=ActionRiskLevel.MEDIUM,
        description="File upload/download",
        requires_confirmation=False,
        dangerous_keywords=["upload", "download", "file", "document"],
    ),
    "navigation": ActionSafetyCheck(
        action_type="navigation",
        risk_level=ActionRiskLevel.LOW,
        description="Page navigation",
        requires_confirmation=False,
        dangerous_keywords=[],
    ),
}


class BrowserSafetyLayer:
    """
    Safety validation for browser automation actions.
    
    Prevents dangerous operations without confirmation.
    """

    def __init__(self, require_confirmations: bool = True):
        self.require_confirmations = require_confirmations
        self.pending_confirmations: dict[str, ActionSafetyCheck] = {}

    def classify_action(
        self,
        action: str,
        context: str = "",
        page_content: str = "",
    ) -> ActionSafetyCheck:
        """
        Classify an action by risk level.
        
        Args:
            action: Action to classify (e.g., 'click', 'fill', 'submit')
            context: Context/description of action
            page_content: Page content/URL for pattern matching
            
        Returns:
            ActionSafetyCheck with risk assessment
        """
        action_lower = action.lower()
        context_lower = context.lower() + " " + page_content.lower()

        # Check for payment actions
        if any(kw in context_lower for kw in DANGEROUS_ACTIONS["payment"].dangerous_keywords):
            return DANGEROUS_ACTIONS["payment"]

        # Check for deletion
        if action_lower in ["delete", "remove"] or any(
            kw in context_lower for kw in DANGEROUS_ACTIONS["deletion"].dangerous_keywords
        ):
            return DANGEROUS_ACTIONS["deletion"]

        # Check for account modifications
        if any(
            kw in context_lower for kw in DANGEROUS_ACTIONS["account_modification"].dangerous_keywords
        ):
            return DANGEROUS_ACTIONS["account_modification"]

        # Check for form submissions
        if action_lower == "submit" or any(
            kw in context_lower for kw in DANGEROUS_ACTIONS["form_submit"].dangerous_keywords
        ):
            return DANGEROUS_ACTIONS["form_submit"]

        # Check for file operations
        if action_lower in ["upload", "download"] or any(
            kw in context_lower for kw in DANGEROUS_ACTIONS["file_operation"].dangerous_keywords
        ):
            return DANGEROUS_ACTIONS["file_operation"]

        # Default to navigation
        return DANGEROUS_ACTIONS["navigation"]

    def should_require_confirmation(self, safety_check: ActionSafetyCheck) -> bool:
        """Check if action requires confirmation."""
        if not self.require_confirmations:
            return False
        return safety_check.requires_confirmation

    def register_pending_action(
        self,
        action_id: str,
        safety_check: ActionSafetyCheck,
    ) -> str:
        """
        Register a pending action requiring confirmation.
        
        Args:
            action_id: Unique ID for the action
            safety_check: Safety classification
            
        Returns:
            Action ID for confirmation
        """
        self.pending_confirmations[action_id] = safety_check
        logger.info(f"Registered pending action {action_id}: {safety_check.description}")
        return action_id

    def confirm_action(self, action_id: str) -> bool:
        """Confirm a pending action."""
        if action_id not in self.pending_confirmations:
            logger.warning(f"Confirmation requested for unknown action {action_id}")
            return False

        del self.pending_confirmations[action_id]
        logger.info(f"Action confirmed: {action_id}")
        return True

    def reject_action(self, action_id: str) -> bool:
        """Reject a pending action."""
        if action_id not in self.pending_confirmations:
            return False

        del self.pending_confirmations[action_id]
        logger.info(f"Action rejected: {action_id}")
        return True

    def get_pending_actions(self) -> dict[str, ActionSafetyCheck]:
        """Get all pending confirmations."""
        return self.pending_confirmations.copy()

    def validate_action_sequence(
        self,
        actions: list[dict],
    ) -> dict[str, list[str]]:
        """
        Validate a sequence of actions for safety issues.
        
        Args:
            actions: List of action dicts with 'type', 'context', 'page_content'
            
        Returns:
            Dict with 'safe_actions', 'risky_actions', 'requires_confirmation'
        """
        safe = []
        risky = []
        requires_conf = []

        for i, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            context = action.get("context", "")
            page_content = action.get("page_content", "")

            check = self.classify_action(action_type, context, page_content)

            action_desc = f"{action_type}: {context}"

            if check.risk_level in (ActionRiskLevel.HIGH, ActionRiskLevel.CRITICAL):
                risky.append(action_desc)
                if self.should_require_confirmation(check):
                    requires_conf.append(action_desc)
            else:
                safe.append(action_desc)

        return {
            "safe_actions": safe,
            "risky_actions": risky,
            "requires_confirmation": requires_conf,
            "total_risky": len(risky),
            "total_confirmation_required": len(requires_conf),
        }

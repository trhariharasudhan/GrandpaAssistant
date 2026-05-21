"""
AI Learning System - Learns from failures and adjusts action strategies.

Provides:
- ActionFailure tracking for pattern analysis
- StrategyAdjuster to learn better selectors
- ConfidenceScorer to assess action reliability
- Pattern recognition for similar tasks
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List, Set
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ActionFailure:
    """Record of a failed action for learning."""
    action_type: str  # click, fill, navigate, extract, etc.
    selector: Optional[str]  # CSS selector that failed
    reason: str  # Why it failed: "not_found", "timeout", "not_visible", etc.
    page_url: Optional[str]  # URL where failure occurred
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    error_message: Optional[str] = None
    context: Optional[str] = None  # Additional context about the page
    
    def to_dict(self):
        return {
            "action_type": self.action_type,
            "selector": self.selector,
            "reason": self.reason,
            "page_url": self.page_url,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "context": self.context,
        }


@dataclass
class SelectorAlternative:
    """Alternative selector for an action with success rate."""
    original_selector: str
    alternative_selector: str
    success_rate: float  # 0-1, how often this works
    times_tried: int = 0
    times_succeeded: int = 0
    discovered_at: datetime = field(default_factory=datetime.now)
    pages_where_it_works: List[str] = field(default_factory=list)  # URL patterns
    
    def to_dict(self):
        return {
            "original": self.original_selector,
            "alternative": self.alternative_selector,
            "success_rate": self.success_rate,
            "times_tried": self.times_tried,
            "times_succeeded": self.times_succeeded,
            "discovered_at": self.discovered_at.isoformat(),
            "pages_where_it_works": self.pages_where_it_works,
        }


@dataclass
class ActionPattern:
    """Learned pattern for similar actions."""
    pattern_id: str  # Hash-based identifier
    action_type: str
    success_count: int = 0
    failure_count: int = 0
    average_confidence: float = 0.5
    common_selectors: Dict[str, int] = field(default_factory=dict)
    common_failures: Dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total
    
    def to_dict(self):
        return {
            "pattern_id": self.pattern_id,
            "action_type": self.action_type,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate(),
            "average_confidence": self.average_confidence,
            "common_selectors": self.common_selectors,
            "common_failures": self.common_failures,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


class ConfidenceScorer:
    """Scores confidence level for planned actions."""
    
    def __init__(self):
        self.action_success_history: Dict[str, List[bool]] = defaultdict(list)
        self.selector_success_rate: Dict[str, float] = {}
        
    def record_result(self, action_type: str, selector: Optional[str], success: bool):
        """Record action result for future scoring."""
        key = f"{action_type}:{selector}"
        self.action_success_history[key].append(success)
        
        # Keep only last 100 results
        if len(self.action_success_history[key]) > 100:
            self.action_success_history[key] = self.action_success_history[key][-100:]
        
        # Update selector success rate
        history = self.action_success_history[key]
        self.selector_success_rate[key] = sum(history) / len(history)
    
    def score_action(
        self,
        action_type: str,
        selector: Optional[str] = None,
        page_url: Optional[str] = None,
        pattern_confidence: float = 0.5,
    ) -> float:
        """
        Score confidence for an action (0-1).
        
        Args:
            action_type: Type of action (click, fill, etc.)
            selector: CSS selector for the action
            page_url: URL of the page
            pattern_confidence: Base confidence from pattern matching
            
        Returns:
            Confidence score 0-1
        """
        base_score = pattern_confidence
        
        # Check historical success rate for this action
        if selector:
            key = f"{action_type}:{selector}"
            if key in self.selector_success_rate:
                historical_rate = self.selector_success_rate[key]
                # Weight: 70% pattern, 30% history
                base_score = (0.7 * base_score) + (0.3 * historical_rate)
        
        # Action type base confidence
        action_base_confidence = {
            "navigate": 0.9,   # Highly reliable
            "click": 0.7,      # Medium reliability
            "fill": 0.75,      # Medium-high reliability
            "extract_text": 0.85,  # High reliability
            "screenshot": 0.95,    # Very reliable
            "submit": 0.7,     # Medium reliability
        }
        
        type_confidence = action_base_confidence.get(action_type, 0.6)
        
        # Final score: average of base and type confidence
        final_score = (base_score + type_confidence) / 2
        
        return min(1.0, max(0.0, final_score))
    
    def get_historical_confidence(self, action_type: str, selector: Optional[str] = None) -> Optional[float]:
        """Get confidence from historical data."""
        if not selector:
            return None
        
        key = f"{action_type}:{selector}"
        return self.selector_success_rate.get(key)


class StrategyAdjuster:
    """Learns better selectors and strategies for actions."""
    
    def __init__(self, memory_limit: int = 1000):
        self.memory_limit = memory_limit
        self.selector_alternatives: Dict[str, List[SelectorAlternative]] = defaultdict(list)
        self.failure_patterns: List[ActionFailure] = []
        self.learned_strategies: Dict[str, Dict[str, Any]] = {}
        
    def add_failure(self, failure: ActionFailure):
        """Record an action failure for learning."""
        self.failure_patterns.append(failure)
        
        # Keep memory manageable
        if len(self.failure_patterns) > self.memory_limit:
            self.failure_patterns = self.failure_patterns[-self.memory_limit:]
        
        logger.info(f"Recorded failure: {failure.action_type} with {failure.reason}")
    
    def learn_alternative_selector(
        self,
        original_selector: str,
        alternative_selector: str,
        success: bool,
        page_url: Optional[str] = None,
    ):
        """Learn that an alternative selector works for a selector that failed."""
        key = original_selector
        
        # Find or create alternative
        alternatives = self.selector_alternatives[key]
        existing = None
        for alt in alternatives:
            if alt.alternative_selector == alternative_selector:
                existing = alt
                break
        
        if existing:
            existing.times_tried += 1
            if success:
                existing.times_succeeded += 1
            existing.success_rate = existing.times_succeeded / existing.times_tried
            if page_url and page_url not in existing.pages_where_it_works:
                existing.pages_where_it_works.append(page_url)
        else:
            alt = SelectorAlternative(
                original_selector=original_selector,
                alternative_selector=alternative_selector,
                success_rate=1.0 if success else 0.0,
                times_tried=1,
                times_succeeded=1 if success else 0,
                pages_where_it_works=[page_url] if page_url else [],
            )
            alternatives.append(alt)
        
        logger.info(f"Learned alternative: {alternative_selector} for {original_selector}")
    
    def get_alternative_selectors(
        self,
        original_selector: str,
        min_success_rate: float = 0.5,
    ) -> List[SelectorAlternative]:
        """Get alternative selectors for a selector."""
        alternatives = self.selector_alternatives.get(original_selector, [])
        
        # Sort by success rate and recency
        sorted_alts = sorted(
            alternatives,
            key=lambda a: (a.success_rate, a.discovered_at),
            reverse=True,
        )
        
        # Return only those above minimum success rate
        return [a for a in sorted_alts if a.success_rate >= min_success_rate]
    
    def analyze_failure_patterns(self) -> Dict[str, Any]:
        """Analyze collected failures to find patterns."""
        if not self.failure_patterns:
            return {}
        
        analysis = {
            "total_failures": len(self.failure_patterns),
            "failures_by_type": defaultdict(int),
            "failures_by_reason": defaultdict(int),
            "failures_by_selector": defaultdict(int),
            "failure_trends": {},
        }
        
        # Group by action type
        for failure in self.failure_patterns:
            analysis["failures_by_type"][failure.action_type] += 1
            analysis["failures_by_reason"][failure.reason] += 1
            if failure.selector:
                analysis["failures_by_selector"][failure.selector] += 1
        
        # Convert defaultdicts to regular dicts
        analysis["failures_by_type"] = dict(analysis["failures_by_type"])
        analysis["failures_by_reason"] = dict(analysis["failures_by_reason"])
        analysis["failures_by_selector"] = dict(analysis["failures_by_selector"])
        
        # Find trends (recent vs older)
        now = datetime.now()
        recent_failures = [f for f in self.failure_patterns if (now - f.timestamp) < timedelta(hours=1)]
        analysis["recent_failure_count"] = len(recent_failures)
        
        return analysis
    
    def suggest_alternative_strategy(
        self,
        action_type: str,
        selector: Optional[str],
        page_url: Optional[str] = None,
    ) -> Optional[str]:
        """Suggest an alternative strategy for a failed action."""
        if not selector:
            return None
        
        alternatives = self.get_alternative_selectors(selector, min_success_rate=0.6)
        
        if alternatives:
            best_alternative = alternatives[0]
            logger.info(f"Suggesting alternative selector: {best_alternative.alternative_selector}")
            return best_alternative.alternative_selector
        
        return None


class PatternRecognizer:
    """Recognizes patterns in action sequences for better learning."""
    
    def __init__(self):
        self.action_patterns: Dict[str, ActionPattern] = {}
        self.seen_action_sequences: List[List[str]] = []
        
    def _generate_pattern_id(self, action_type: str, context: Optional[str] = None) -> str:
        """Generate a hash-based pattern ID."""
        key = f"{action_type}:{context or 'generic'}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
    
    def record_action(
        self,
        action_type: str,
        selector: Optional[str],
        success: bool,
        context: Optional[str] = None,
    ):
        """Record an action for pattern analysis."""
        pattern_id = self._generate_pattern_id(action_type, context)
        
        if pattern_id not in self.action_patterns:
            self.action_patterns[pattern_id] = ActionPattern(
                pattern_id=pattern_id,
                action_type=action_type,
            )
        
        pattern = self.action_patterns[pattern_id]
        
        if success:
            pattern.success_count += 1
        else:
            pattern.failure_count += 1
        
        # Track common selectors
        if selector:
            pattern.common_selectors[selector] = pattern.common_selectors.get(selector, 0) + 1
        
        pattern.last_updated = datetime.now()
        
        # Update average confidence
        total = pattern.success_count + pattern.failure_count
        if total > 0:
            pattern.average_confidence = pattern.success_count / total
    
    def record_failure_reason(
        self,
        action_type: str,
        reason: str,
        context: Optional[str] = None,
    ):
        """Record why an action failed for pattern analysis."""
        pattern_id = self._generate_pattern_id(action_type, context)
        
        if pattern_id not in self.action_patterns:
            self.action_patterns[pattern_id] = ActionPattern(
                pattern_id=pattern_id,
                action_type=action_type,
            )
        
        pattern = self.action_patterns[pattern_id]
        pattern.common_failures[reason] = pattern.common_failures.get(reason, 0) + 1
    
    def get_pattern(self, action_type: str, context: Optional[str] = None) -> Optional[ActionPattern]:
        """Get learned pattern for an action type."""
        pattern_id = self._generate_pattern_id(action_type, context)
        return self.action_patterns.get(pattern_id)
    
    def get_best_selectors(self, action_type: str, context: Optional[str] = None, limit: int = 3) -> List[str]:
        """Get the best performing selectors for an action type."""
        pattern = self.get_pattern(action_type, context)
        if not pattern:
            return []
        
        # Sort selectors by frequency (popularity)
        sorted_selectors = sorted(
            pattern.common_selectors.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        return [selector for selector, _ in sorted_selectors[:limit]]
    
    def get_patterns_summary(self) -> Dict[str, Any]:
        """Get summary of all learned patterns."""
        summary = {
            "total_patterns": len(self.action_patterns),
            "patterns_by_type": defaultdict(int),
            "high_confidence_patterns": [],
            "low_confidence_patterns": [],
        }
        
        for pattern_id, pattern in self.action_patterns.items():
            summary["patterns_by_type"][pattern.action_type] += 1
            
            if pattern.average_confidence >= 0.8:
                summary["high_confidence_patterns"].append({
                    "action_type": pattern.action_type,
                    "confidence": pattern.average_confidence,
                    "success_count": pattern.success_count,
                })
            elif pattern.average_confidence <= 0.3:
                summary["low_confidence_patterns"].append({
                    "action_type": pattern.action_type,
                    "confidence": pattern.average_confidence,
                    "failure_count": pattern.failure_count,
                })
        
        summary["patterns_by_type"] = dict(summary["patterns_by_type"])
        return summary


class AILearningSystem:
    """
    Integrated AI learning system for browser automation.
    
    Combines confidence scoring, strategy adjustment, and pattern recognition.
    """
    
    def __init__(self):
        self.confidence_scorer = ConfidenceScorer()
        self.strategy_adjuster = StrategyAdjuster()
        self.pattern_recognizer = PatternRecognizer()
        self.learning_enabled = True
        
        logger.info("AILearningSystem initialized")
    
    def record_action_execution(
        self,
        action_type: str,
        selector: Optional[str],
        success: bool,
        reason: Optional[str] = None,
        page_url: Optional[str] = None,
        context: Optional[str] = None,
    ):
        """Record an executed action for learning."""
        if not self.learning_enabled:
            return
        
        # Record with confidence scorer
        self.confidence_scorer.record_result(action_type, selector, success)
        
        # Record with pattern recognizer
        self.pattern_recognizer.record_action(action_type, selector, success, context)
        
        # If failed, record failure
        if not success and reason:
            failure = ActionFailure(
                action_type=action_type,
                selector=selector,
                reason=reason,
                page_url=page_url,
                context=context,
            )
            self.strategy_adjuster.add_failure(failure)
            self.pattern_recognizer.record_failure_reason(action_type, reason, context)
    
    def score_action_plan(self, actions: List[Dict[str, Any]]) -> float:
        """Score confidence for an entire action plan (0-1)."""
        if not actions:
            return 0.5
        
        scores = []
        for action in actions:
            action_type = action.get("action_type", "unknown")
            selector = action.get("selector")
            
            pattern = self.pattern_recognizer.get_pattern(action_type)
            pattern_confidence = pattern.average_confidence if pattern else 0.5
            
            score = self.confidence_scorer.score_action(
                action_type,
                selector,
                pattern_confidence=pattern_confidence,
            )
            scores.append(score)
        
        # Overall confidence is average of individual scores, with penalty for multiple actions
        base_score = sum(scores) / len(scores)
        complexity_penalty = 0.02 * (len(actions) - 1)  # Small penalty per extra action
        
        final_score = base_score - complexity_penalty
        return min(1.0, max(0.0, final_score))
    
    def get_fallback_selector(
        self,
        original_selector: str,
        action_type: str,
    ) -> Optional[str]:
        """Get a fallback selector for a failed action."""
        return self.strategy_adjuster.suggest_alternative_strategy(
            action_type,
            original_selector,
        )
    
    def learn_alternative_selector(
        self,
        original_selector: str,
        alternative_selector: str,
        success: bool,
        page_url: Optional[str] = None,
    ):
        """Learn an alternative selector that works."""
        self.strategy_adjuster.learn_alternative_selector(
            original_selector,
            alternative_selector,
            success,
            page_url,
        )
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get summary of what the system has learned."""
        return {
            "failure_analysis": self.strategy_adjuster.analyze_failure_patterns(),
            "patterns_summary": self.pattern_recognizer.get_patterns_summary(),
            "selector_alternatives_count": sum(
                len(alts) for alts in self.strategy_adjuster.selector_alternatives.values()
            ),
        }
    
    def enable_learning(self, enabled: bool = True):
        """Enable or disable learning."""
        self.learning_enabled = enabled
        logger.info(f"Learning {'enabled' if enabled else 'disabled'}")

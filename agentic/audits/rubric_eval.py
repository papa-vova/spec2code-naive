"""Semantic rubric evaluator abstractions and defaults."""

from __future__ import annotations

from typing import Any, Dict, Protocol


class SemanticEvaluator(Protocol):
    """Semantic evaluator contract for rubric-driven decisions."""

    def evaluate(self, artifacts: Dict[str, Dict[str, Any]], rubric: str | None = None) -> Dict[str, Any]:
        """Return semantic evaluation with confidence and evidence."""


class DefaultSemanticEvaluator:
    """Default semantic evaluator with deterministic fallback behavior."""

    def evaluate(self, artifacts: Dict[str, Dict[str, Any]], rubric: str | None = None) -> Dict[str, Any]:
        # M3 default: no external rubric -> neutral pass with full confidence.
        return {
            "confidence_score": 1.0,
            "blocking_gaps": [],
            "evidence_refs": sorted(artifacts.keys()),
            "rubric_ref": rubric,
        }


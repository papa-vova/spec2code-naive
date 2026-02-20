"""Audit gate orchestration helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from agentic.audits.checks import check_completeness, check_consistency, check_traceability
from agentic.audits.rubric_eval import DefaultSemanticEvaluator
from agentic.artifacts.models import InfoSufficiencyAssessmentContent


def run_sufficiency_evaluation(
    pipeline_input: Dict[str, Any],
    min_content_size: int,
    insufficient_markers: List[str],
) -> InfoSufficiencyAssessmentContent:
    """Produce rule-based information sufficiency assessment."""
    content = str(pipeline_input.get("content", ""))
    size = int(pipeline_input.get("size", len(content)))

    confidence = 1.0
    blocking_gaps: List[Dict[str, Any]] = []

    if size < min_content_size:
        confidence -= 0.5
        blocking_gaps.append(
            {
                "area": "scope",
                "description": "Description is too short for implementation planning.",
                "suggested_question": "What are the key goals, constraints, and acceptance criteria?",
            }
        )

    upper_content = content.upper()
    found_markers = [marker for marker in insufficient_markers if marker.upper() in upper_content]
    if found_markers:
        confidence -= 0.3
        blocking_gaps.append(
            {
                "area": "unknowns",
                "description": "Input contains unresolved placeholders.",
                "suggested_question": "Can you resolve placeholders before planning?",
                "markers": found_markers,
            }
        )

    confidence = max(0.0, min(1.0, confidence))
    return InfoSufficiencyAssessmentContent(
        confidence_score=confidence,
        blocking_gaps=blocking_gaps,
    )


def run_deterministic_audit(artifacts: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Run deterministic audit checks across produced artifacts."""
    errors: List[str] = []
    per_artifact_completeness: Dict[str, List[str]] = {}

    traceability_errors = check_traceability(artifacts)
    consistency_errors = check_consistency(artifacts)
    errors.extend(traceability_errors)
    errors.extend(consistency_errors)

    for artifact_type, content in artifacts.items():
        completeness_errors = check_completeness(content)
        if completeness_errors:
            per_artifact_completeness[artifact_type] = completeness_errors
            errors.extend([f"{artifact_type}: {entry}" for entry in completeness_errors])

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "results": {
            "traceability": traceability_errors,
            "consistency": consistency_errors,
            "completeness": per_artifact_completeness,
        },
    }


def run_semantic_audit(artifacts: Dict[str, Dict[str, Any]], rubric: str | None = None) -> Dict[str, Any]:
    """Run semantic evaluation using the default evaluator."""
    evaluator = DefaultSemanticEvaluator()
    return evaluator.evaluate(artifacts, rubric)


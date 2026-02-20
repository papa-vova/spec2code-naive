"""Deterministic audit checks for run artifacts."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set


def _walk_strings(payload: Any) -> List[str]:
    """Extract all leaf strings from nested structures."""
    strings: List[str] = []
    if isinstance(payload, str):
        strings.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            strings.extend(_walk_strings(value))
    elif isinstance(payload, list):
        for item in payload:
            strings.extend(_walk_strings(item))
    return strings


def extract_stable_ids(artifact_content: Dict[str, Any], id_prefix: str) -> List[str]:
    """Extract stable IDs like REQ-0001 from nested artifact content."""
    pattern = re.compile(rf"\b{re.escape(id_prefix)}-\d{{4}}\b")
    matches: Set[str] = set()
    for text in _walk_strings(artifact_content):
        matches.update(pattern.findall(text))
    return sorted(matches)


def check_traceability(artifacts: Dict[str, Dict[str, Any]]) -> List[str]:
    """Validate minimal traceability links between requirements and objectives/tasks."""
    errors: List[str] = []

    objective_ids = extract_stable_ids(artifacts.get("ProblemBrief", {}), "OBJ")
    requirement_ids = extract_stable_ids(artifacts.get("ImplementableSpec", {}), "REQ")
    task_links = extract_stable_ids(artifacts.get("WorkBreakdown", {}), "REQ")

    if requirement_ids and not objective_ids:
        errors.append("Requirements exist but no objective IDs were found for traceability.")
    if requirement_ids and not task_links:
        errors.append("Requirements exist but no task-to-requirement trace links were found.")

    return errors


def check_completeness(artifact_content: Dict[str, Any]) -> List[str]:
    """Check for unresolved placeholders in content."""
    errors: List[str] = []
    unresolved_markers = ("TBD", "TODO", "TO_BE_DEFINED")
    upper_strings = [text.upper() for text in _walk_strings(artifact_content)]
    for marker in unresolved_markers:
        if any(marker in text for text in upper_strings):
            errors.append(f"Unresolved marker detected: {marker}")
    return errors


def check_consistency(artifacts: Dict[str, Dict[str, Any]]) -> List[str]:
    """Check simple contradictions in non-functional requirements."""
    errors: List[str] = []
    nfr_text = " ".join(_walk_strings(artifacts.get("NonFunctionalRequirements", {}))).lower()
    adr_text = " ".join(_walk_strings(artifacts.get("ArchitectureDecisionRecordSet", {}))).lower()

    contradictions = [
        ("eventual consistency", "strong consistency"),
        ("single region only", "multi-region required"),
    ]
    for left, right in contradictions:
        if left in nfr_text and right in nfr_text and "tradeoff" not in adr_text:
            errors.append(f"Potential contradiction without ADR tradeoff: {left} vs {right}.")

    return errors


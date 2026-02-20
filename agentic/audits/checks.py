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


def check_3nf_data_structures(
    artifacts: Dict[str, Dict[str, Any]], require_3nf: bool
) -> List[str]:
    """Verify 3NF data structures when ImplementationDesign exists and require_3nf is true."""
    errors: List[str] = []
    if not require_3nf:
        return errors

    impl_design = artifacts.get("ImplementationDesign", {})
    if not impl_design:
        return errors

    data_structures = impl_design.get("data_structures", [])
    if not isinstance(data_structures, list):
        errors.append("ImplementationDesign.data_structures must be a list.")
        return errors

    if len(data_structures) == 0:
        errors.append("ImplementationDesign must include at least one data_structures entry when require_3nf_data_structures is enabled.")
        return errors

    for i, entry in enumerate(data_structures):
        if not isinstance(entry, dict):
            errors.append(f"ImplementationDesign.data_structures[{i}] must be an object.")
            continue
        norm_level = entry.get("normalization_level")
        if not norm_level:
            errors.append(f"ImplementationDesign.data_structures[{i}] missing normalization_level.")
        elif str(norm_level).upper() != "3NF":
            rationale = entry.get("denormalization_rationale")
            if not rationale or not str(rationale).strip():
                errors.append(
                    f"ImplementationDesign.data_structures[{i}] has normalization_level '{norm_level}' "
                    "but missing denormalization_rationale."
                )

    return errors


def check_performance_guidance(
    artifacts: Dict[str, Dict[str, Any]], require_performance: bool
) -> List[str]:
    """Verify performance guidance when ImplementationDesign exists and require_performance is true."""
    errors: List[str] = []
    if not require_performance:
        return errors

    impl_design = artifacts.get("ImplementationDesign", {})
    if not impl_design:
        return errors

    perf_guidance = impl_design.get("performance_guidance", [])
    modules = impl_design.get("modules", [])
    if not isinstance(perf_guidance, list):
        perf_guidance = []
    if not isinstance(modules, list):
        modules = []

    has_perf_entries = len(perf_guidance) > 0
    modules_with_complexity = sum(
        1 for m in modules if isinstance(m, dict) and m.get("complexity")
    )

    if not has_perf_entries and modules_with_complexity == 0:
        errors.append(
            "ImplementationDesign must include performance_guidance entries or module-level complexity "
            "when require_performance_guidance is enabled."
        )

    return errors


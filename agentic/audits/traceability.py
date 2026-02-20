"""Traceability matrix generation from persisted run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from agentic.audits.checks import extract_stable_ids
from agentic.artifacts.models import TraceabilityMatrixContent
from agentic.artifacts.store import ArtifactStore


def _load_artifact_contents(artifact_store: ArtifactStore, run_id: str) -> Dict[str, Dict[str, Any]]:
    """Load raw content payloads for all persisted artifacts in a run."""
    artifacts_dir = artifact_store.get_run_directory(run_id) / "artifacts"
    if not artifacts_dir.exists():
        return {}

    contents: Dict[str, Dict[str, Any]] = {}
    for artifact_path in artifacts_dir.glob("*.json"):
        with open(artifact_path, "r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        artifact_type = payload.get("identity", {}).get("artifact_type")
        content = payload.get("content")
        if isinstance(artifact_type, str) and isinstance(content, dict):
            contents[artifact_type] = content
    return contents


def build_traceability_matrix(artifact_store: ArtifactStore, run_id: str) -> TraceabilityMatrixContent:
    """Build a traceability matrix from artifacts in the run directory."""
    contents = _load_artifact_contents(artifact_store, run_id)

    rows = extract_stable_ids(contents.get("ImplementableSpec", {}), "REQ")

    column_prefixes = ("OBJ", "ADR", "DES", "TASK", "TEST")
    columns_set: Set[str] = set()
    for prefix in column_prefixes:
        for artifact_content in contents.values():
            columns_set.update(extract_stable_ids(artifact_content, prefix))
    columns = sorted(columns_set)

    content_texts = {
        artifact_type: json.dumps(content, ensure_ascii=False)
        for artifact_type, content in contents.items()
    }
    cells: Dict[str, List[str]] = {}
    gaps: List[Dict[str, Any]] = []
    for row in rows:
        matched_columns: List[str] = []
        for column in columns:
            for artifact_type, text in content_texts.items():
                if row in text and column in text:
                    matched_columns.append(column)
                    break
        for column in matched_columns:
            key = f"{row}|{column}"
            cells[key] = [row, column]
        if not matched_columns:
            gaps.append({"row_id": row, "column_id": None, "severity": "high"})

    return TraceabilityMatrixContent(
        rows=rows,
        columns=columns,
        cells=cells,
        gaps=gaps,
    )


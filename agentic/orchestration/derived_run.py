"""
Derived run logic: load base run, apply amendment, re-execute pipeline.

A formal amendment triggers a derived run that deterministically recomputes
dependent artifacts with base_run_id in provenance.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from agentic.artifacts.models import ArtifactType
from agentic.artifacts.store import ArtifactStore


def load_base_run_metadata(artifact_store: ArtifactStore, base_run_id: str) -> Dict[str, Any]:
    """Load metadata from a base run."""
    metadata_path = artifact_store.get_run_directory(base_run_id) / "metadata.json"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Base run metadata not found: {metadata_path}")
    with open(metadata_path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def load_amendment(amendment_path: str) -> Dict[str, Any]:
    """Load amendment JSON with base_run_id, amended_assumptions, amended_tradeoffs."""
    path = Path(amendment_path)
    if not path.exists():
        raise FileNotFoundError(f"Amendment file not found: {path}")
    with open(path, "r", encoding="utf-8") as file_obj:
        data = json.load(file_obj)
    if "base_run_id" not in data:
        raise ValueError("Amendment must contain base_run_id")
    return data


def apply_amendment(
    base_metadata: Dict[str, Any],
    amendment: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge amendment into pipeline input for derived run.

    Returns pipeline_input with amended_assumptions and amended_tradeoffs
    merged for agents to consume.
    """
    pipeline_input = dict(base_metadata.get("pipeline_input", {}))
    if not pipeline_input or "content" not in pipeline_input:
        raise ValueError(
            "Base run metadata must contain pipeline_input for derived run replay. "
            "Ensure the base run was created with a version that stores pipeline_input."
        )

    amended_assumptions = amendment.get("amended_assumptions", [])
    amended_tradeoffs = amendment.get("amended_tradeoffs", [])

    if amended_assumptions or amended_tradeoffs:
        pipeline_input["amended_context"] = {
            "amended_assumptions": amended_assumptions,
            "amended_tradeoffs": amended_tradeoffs,
            "reason": amendment.get("reason"),
        }
    return pipeline_input


def run_derived_pipeline(
    artifact_store: ArtifactStore,
    orchestrator: Any,
    base_run_id: str,
    amendment_path: str,
    config_root: str,
) -> Dict[str, Any]:
    """
    Execute a derived run: load base, apply amendment, re-run pipeline.

    Returns orchestrator result with run_id and base_run_id.
    """
    base_metadata = load_base_run_metadata(artifact_store, base_run_id)
    amendment = load_amendment(amendment_path)

    if amendment.get("base_run_id") != base_run_id:
        raise ValueError(
            f"Amendment base_run_id '{amendment.get('base_run_id')}' "
            f"does not match --base-run '{base_run_id}'"
        )

    pipeline_input = apply_amendment(base_metadata, amendment)

    run_id = artifact_store.generate_run_id()
    run_dir = artifact_store.initialize_run(run_id)

    from agentic.collaboration.event_log import CollaborationEventLog

    collaboration_event_log = (
        CollaborationEventLog(artifact_store.get_collaboration_dir(run_id))
        if run_dir is not None
        else None
    )

    result = orchestrator.execute_pipeline(
        input_data=pipeline_input,
        run_id=run_id,
        artifact_store=artifact_store,
        collaboration_event_log=collaboration_event_log,
        base_run_id=base_run_id,
    )

    result["run_id"] = run_id
    result["base_run_id"] = base_run_id

    if artifact_store.create_artifacts:
        artifact_store.write_metadata(
            run_id=run_id,
            config_root=config_root,
            input_file=base_metadata.get("input_file"),
            pipeline_name=result.get("pipeline_name", "unknown"),
            execution_successful=result.get("execution_successful", False),
            total_execution_time=result.get("metadata", {}).get("execution_time", 0),
            artifacts_manifest=result.get("artifacts_manifest", []),
            pipeline_input=pipeline_input,
            base_run_id=base_run_id,
        )

    return result

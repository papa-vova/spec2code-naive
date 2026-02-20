"""Artifact storage for run-scoped canonical artifacts."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agentic.artifacts.models import Artifact


class ArtifactStore:
    """Manages run directories and artifact persistence."""

    def __init__(self, runs_directory: str = "runs", create_artifacts: bool = True):
        self.runs_directory = Path(runs_directory)
        self.create_artifacts = create_artifacts
        if self.create_artifacts:
            self.runs_directory.mkdir(parents=True, exist_ok=True)

    def generate_run_id(self) -> str:
        """Generate unique run ID using UTC timestamp + short UUID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        run_id = f"{timestamp}_{short_uuid}"

        run_dir = self.runs_directory / run_id
        counter = 1
        original = run_id
        while run_dir.exists():
            run_id = f"{original}_{counter}"
            run_dir = self.runs_directory / run_id
            counter += 1
        return run_id

    def get_run_directory(self, run_id: str) -> Path:
        """Return run directory path for run ID."""
        return self.runs_directory / run_id

    def initialize_run(self, run_id: str) -> Optional[Path]:
        """Create run folder layout for the run."""
        if not self.create_artifacts:
            return None
        run_dir = self.get_run_directory(run_id)
        (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (run_dir / "collaboration").mkdir(parents=True, exist_ok=True)
        return run_dir

    def get_collaboration_dir(self, run_id: str) -> Path:
        """Return run collaboration directory path for run ID."""
        return self.get_run_directory(run_id) / "collaboration"

    def write_artifact(self, run_id: str, artifact: Artifact) -> Optional[Path]:
        """Persist artifact JSON under run artifacts folder."""
        if not self.create_artifacts:
            return None
        run_dir = self.initialize_run(run_id)
        artifact_path = run_dir / "artifacts" / f"{artifact.identity.artifact_type.value}.json"
        with open(artifact_path, "w", encoding="utf-8") as file_obj:
            json.dump(artifact.model_dump(mode="json"), file_obj, indent=2, ensure_ascii=False)
        return artifact_path

    def read_artifact(self, run_id: str, artifact_type: str) -> Artifact:
        """Read and validate persisted artifact by type name."""
        artifact_path = self.get_run_directory(run_id) / "artifacts" / f"{artifact_type}.json"
        with open(artifact_path, "r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
        return Artifact.model_validate(payload)

    def write_metadata(
        self,
        run_id: str,
        config_root: str,
        input_file: Optional[str],
        pipeline_name: str,
        execution_successful: bool,
        total_execution_time: float,
        artifacts_manifest: List[Dict[str, Any]],
    ) -> Optional[Path]:
        """Persist run metadata with artifact manifest."""
        if not self.create_artifacts:
            return None
        run_dir = self.initialize_run(run_id)
        metadata_path = run_dir / "metadata.json"
        metadata = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config_root": str(Path(config_root).resolve()),
            "input_file": str(Path(input_file).resolve()) if input_file else None,
            "pipeline_name": pipeline_name,
            "execution_successful": execution_successful,
            "total_execution_time": total_execution_time,
            "artifacts_manifest": artifacts_manifest,
        }
        with open(metadata_path, "w", encoding="utf-8") as file_obj:
            json.dump(metadata, file_obj, indent=2, ensure_ascii=False)
        return metadata_path


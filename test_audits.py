#!/usr/bin/env python3
"""Tests for Milestone 3 audit gates, sufficiency, and stop logic."""

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from agentic.audits.checks import (
    check_completeness,
    check_traceability,
    extract_stable_ids,
)
from agentic.audits.gates import run_deterministic_audit, run_sufficiency_evaluation
from agentic.audits.traceability import build_traceability_matrix
from agentic.artifacts.models import (
    Artifact,
    ArtifactIdentity,
    ArtifactProvenance,
    ArtifactType,
    ModelConfigRef,
    PromptRef,
    compute_content_hash,
)
from agentic.artifacts.store import ArtifactStore
from config_system.config_loader import ConfigLoader
from main import Pipeline


class AuditTestBase(unittest.TestCase):
    """Shared fixture helpers for audit tests."""

    def _write_minimal_config(self, root: Path, *, min_confidence: float = 0.6, min_input_size: int = 120):
        (root / "models").mkdir(parents=True, exist_ok=True)
        (root / "agents" / "test_role").mkdir(parents=True, exist_ok=True)

        (root / "models" / "test_model.yaml").write_text(
            yaml.safe_dump(
                {
                    "name": "test_model",
                    "provider": "OpenAI",
                    "model_name": "gpt-5-mini",
                    "parameters": {},
                    "credentials": {"api_key": "${OPENAI_API_KEY}"},
                }
            ),
            encoding="utf-8",
        )
        (root / "agents" / "test_role" / "agent.yaml").write_text(
            yaml.safe_dump({"name": "test_role", "description": "test role", "llm": "test_model"}),
            encoding="utf-8",
        )
        (root / "agents" / "test_role" / "prompts.yaml").write_text(
            yaml.safe_dump(
                {
                    "system_message": "You are test role",
                    "human_message_template": "Input: {input}",
                    "prompt_templates": {"default": "Return json"},
                }
            ),
            encoding="utf-8",
        )
        (root / "pipeline.yaml").write_text(
            yaml.safe_dump(
                {
                    "pipeline": {
                        "name": "test_pipeline",
                        "description": "test",
                        "agents": [{"name": "test_role", "inputs": ["pipeline_input"]}],
                        "execution": {"mode": "sequential"},
                        "settings": {
                            "log_level": "ERROR",
                            "create_run_artifacts": True,
                            "include_messages_in_artifacts": False,
                            "runs_directory": str(root / "runs"),
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / "agentic.yaml").write_text(
            yaml.safe_dump(
                {
                    "role_model_profiles": {"test_role": {"model": "test_model"}},
                    "audit": {
                        "min_confidence_to_proceed": min_confidence,
                        "min_input_size_for_sufficiency": min_input_size,
                        "insufficient_markers": ["TBD", "TODO"],
                        "sufficiency_rubric": None,
                    },
                }
            ),
            encoding="utf-8",
        )


class TestDeterministicChecks(unittest.TestCase):
    """Unit tests for deterministic audit checks."""

    def test_extract_stable_ids(self):
        content = {"a": "REQ-0001 OBJ-0002", "nested": [{"x": "REQ-0003"}]}
        ids = extract_stable_ids(content, "REQ")
        self.assertEqual(ids, ["REQ-0001", "REQ-0003"])

    def test_traceability_and_completeness_checks(self):
        artifacts = {
            "ImplementableSpec": {"items": [{"id": "REQ-0001"}]},
            "ProblemBrief": {"goals": [{"id": "OBJ-0001"}]},
            "WorkBreakdown": {"tasks": [{"requirement_ids": ["REQ-0001"]}]},
        }
        self.assertEqual(check_traceability(artifacts), [])
        self.assertTrue(check_completeness({"text": "TBD section"}))

    def test_run_deterministic_audit(self):
        artifacts = {"BusinessRequirements": {"title": "Feature", "notes": "TODO add details"}}
        results = run_deterministic_audit(artifacts)
        self.assertFalse(results["passed"])
        self.assertTrue(results["errors"])


class TestSufficiencyEvaluation(unittest.TestCase):
    """Unit tests for sufficiency evaluation."""

    def test_low_and_high_confidence_paths(self):
        low = run_sufficiency_evaluation(
            pipeline_input={"content": "short TBD", "size": 9},
            min_content_size=120,
            insufficient_markers=["TBD", "TODO"],
        )
        self.assertLess(low.confidence_score or 1.0, 0.6)
        self.assertTrue(low.blocking_gaps)

        high = run_sufficiency_evaluation(
            pipeline_input={"content": "x" * 200, "size": 200},
            min_content_size=120,
            insufficient_markers=["TBD", "TODO"],
        )
        self.assertGreaterEqual(high.confidence_score or 0.0, 0.9)
        self.assertEqual(high.blocking_gaps, [])


class TestTraceabilityMatrix(unittest.TestCase):
    """Traceability matrix generation tests."""

    def test_build_traceability_matrix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ArtifactStore(runs_directory=temp_dir, create_artifacts=True)
            run_id = store.generate_run_id()
            store.initialize_run(run_id)

            req_content = {"requirements": [{"id": "REQ-0001"}, {"id": "REQ-0002"}], "link": "OBJ-0001"}
            req_artifact = Artifact(
                identity=ArtifactIdentity(
                    artifact_id="ImplementableSpec",
                    artifact_type=ArtifactType.IMPLEMENTABLE_SPEC,
                    schema_version="1.0.0",
                ),
                provenance=ArtifactProvenance(
                    run_id=run_id,
                    created_at="2026-02-20T00:00:00+00:00",
                    created_by_role="system_analyst",
                    created_by_agent_instance_id="a1",
                    model_config_ref=ModelConfigRef(provider="OpenAI", model_name="gpt-5-mini", parameters={}),
                    role_model_profile_id="system_analyst",
                    prompt_ref=PromptRef(template_name="default", template_version="v1"),
                ),
                content=req_content,
                content_hash=compute_content_hash(req_content),
            )
            store.write_artifact(run_id, req_artifact)

            matrix = build_traceability_matrix(store, run_id)
            self.assertIn("REQ-0001", matrix.rows)
            self.assertIn("OBJ-0001", matrix.columns)


class TestAuditStorageAndStopLogic(AuditTestBase):
    """Integration tests for audit persistence and orchestrator stop behavior."""

    def test_write_audit_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ArtifactStore(runs_directory=temp_dir, create_artifacts=True)
            run_id = store.generate_run_id()
            store.initialize_run(run_id)
            path = store.write_audit_results(run_id, {"deterministic": {"passed": True}})
            self.assertTrue(path.exists())
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload["deterministic"]["passed"])

    def test_config_min_confidence(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_config(root, min_confidence=0.77)
            loader = ConfigLoader(str(root))
            self.assertEqual(loader.get_min_confidence_to_proceed(), 0.77)

    def test_pipeline_stops_on_insufficient_information(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_config(root, min_confidence=0.9, min_input_size=500)

            pipeline = Pipeline(config_root=str(root), dry_run=True)
            result = pipeline.run_pipeline("short", f"{temp_dir}/input.txt")

            self.assertFalse(result["execution_successful"])
            self.assertTrue(result["metadata"]["blocking_gaps"])

            run_id = result["run_id"]
            assessment_path = (
                root / "runs" / run_id / "artifacts" / "InfoSufficiencyAssessment.json"
            )
            self.assertTrue(assessment_path.exists())

            audit_path = root / "runs" / run_id / "audits" / "audit_results.json"
            self.assertTrue(audit_path.exists())

            events_path = root / "runs" / run_id / "collaboration" / "collaboration_events.jsonl"
            self.assertTrue(events_path.exists())
            event_lines = events_path.read_text(encoding="utf-8")
            self.assertIn("audit_gate_failed", event_lines)


if __name__ == "__main__":
    unittest.main()


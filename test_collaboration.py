#!/usr/bin/env python3
"""Tests for collaboration artifacts, logging, and integration."""

import io
import json
import tempfile
import unittest
import uuid
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path

import yaml

from agentic.artifacts.store import ArtifactStore
from agentic.collaboration.event_log import CollaborationEventLog
from agentic.collaboration.models import (
    CollaborationEvent,
    CollaborationEventType,
    ContentRef,
)
from agentic.collaboration.transcript_store import TranscriptStore, hash_text
from logging_config import setup_pipeline_logging
from main import Pipeline
from scripts import export_schemas


class CollaborationTestBase(unittest.TestCase):
    """Shared helpers for collaboration integration tests."""

    def _write_minimal_config(self, root: Path) -> None:
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
            yaml.safe_dump(
                {
                    "name": "test_role",
                    "description": "test role",
                    "llm": "test_model",
                }
            ),
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
            yaml.safe_dump({"role_model_profiles": {"test_role": {"model": "test_model"}}}),
            encoding="utf-8",
        )


class TestCollaborationModels(unittest.TestCase):
    """Model-level tests for collaboration event payloads."""

    def test_collaboration_event_roundtrip(self):
        event = CollaborationEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id="run-1",
            actor="orchestrator",
            event_type=CollaborationEventType.ORCHESTRATOR_DECISION_MADE,
            references=["BusinessRequirements"],
            content_ref=ContentRef(path="collaboration/blob.txt", content_hash="sha256:abc"),
            summary="Pipeline execution started",
        )
        payload = event.model_dump(mode="json")
        roundtrip = CollaborationEvent.model_validate(payload)

        self.assertEqual(roundtrip.run_id, "run-1")
        self.assertIsNotNone(datetime.fromisoformat(roundtrip.timestamp).tzinfo)
        self.assertEqual(roundtrip.event_type, CollaborationEventType.ORCHESTRATOR_DECISION_MADE)
        self.assertEqual(roundtrip.content_ref.path, "collaboration/blob.txt")
        self.assertIsInstance(uuid.UUID(roundtrip.event_id), uuid.UUID)


class TestCollaborationEventLog(unittest.TestCase):
    """JSONL event log behavior tests."""

    def test_emit_read_filter_and_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            collaboration_dir = Path(temp_dir) / "collaboration"
            event_log = CollaborationEventLog(collaboration_dir)

            event_types = [
                CollaborationEventType.ORCHESTRATOR_DECISION_MADE,
                CollaborationEventType.ARTIFACT_PRODUCED,
                CollaborationEventType.ORCHESTRATOR_DECISION_MADE,
            ]
            for index, event_type in enumerate(event_types):
                event_log.emit(
                    CollaborationEvent(
                        event_id=str(uuid.uuid4()),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        run_id="run-1",
                        actor="orchestrator",
                        event_type=event_type,
                        references=[f"ref-{index}"],
                        summary=f"summary-{index}",
                    )
                )

            all_events = event_log.read_all()
            decision_events = event_log.read_by_type(
                CollaborationEventType.ORCHESTRATOR_DECISION_MADE
            )
            self.assertEqual(len(all_events), 3)
            self.assertEqual(len(decision_events), 2)
            self.assertEqual(event_log.count(), 3)
            for event in all_events:
                self.assertIsNotNone(datetime.fromisoformat(event.timestamp).tzinfo)

            events_file = collaboration_dir / "collaboration_events.jsonl"
            raw_lines = [line for line in events_file.read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(len(raw_lines), 3)
            for line in raw_lines:
                json.loads(line)


class TestTranscriptStore(unittest.TestCase):
    """Plain-file transcript store behavior tests."""

    def test_write_read_and_hash(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            collaboration_dir = Path(temp_dir) / "collaboration"
            transcript_store = TranscriptStore(collaboration_dir)

            transcript_path, transcript_hash = transcript_store.write_entry(
                role="product_owner",
                content="Need latency under 100ms",
            )
            self.assertEqual(transcript_path, "stakeholder_transcript.txt")
            self.assertTrue(transcript_hash.startswith("sha256:"))

            blob_path, blob_hash = transcript_store.write_content_file(
                "q1.txt", "What are your availability requirements?"
            )
            self.assertEqual(blob_path, "q1.txt")
            self.assertEqual(blob_hash, hash_text("What are your availability requirements?"))

            transcript = transcript_store.read_transcript()
            self.assertIn("product_owner", transcript)
            self.assertIn("Need latency under 100ms", transcript)


class TestCollaborationIntegration(CollaborationTestBase):
    """Integration tests for run scaffolding and orchestrator event emission."""

    def test_artifact_store_initializes_collaboration_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ArtifactStore(runs_directory=temp_dir, create_artifacts=True)
            run_id = store.generate_run_id()
            run_dir = store.initialize_run(run_id)
            self.assertTrue((run_dir / "collaboration").exists())
            self.assertEqual(store.get_collaboration_dir(run_id), run_dir / "collaboration")

    def test_pipeline_dry_run_emits_collaboration_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_config(root)
            pipeline = Pipeline(config_root=str(root), dry_run=True)
            result = pipeline.run_pipeline("hello world", f"{temp_dir}/input.txt")

            run_id = result["run_id"]
            events_path = root / "runs" / run_id / "collaboration" / "collaboration_events.jsonl"
            self.assertTrue(events_path.exists())

            event_log = CollaborationEventLog(events_path.parent)
            events = event_log.read_all()
            event_types = [event.event_type for event in events]
            self.assertIn(CollaborationEventType.ORCHESTRATOR_DECISION_MADE, event_types)
            self.assertIn(CollaborationEventType.ARTIFACT_PRODUCED, event_types)

            produced_events = [
                event for event in events if event.event_type == CollaborationEventType.ARTIFACT_PRODUCED
            ]
            self.assertGreaterEqual(len(produced_events), 1)
            self.assertEqual(produced_events[0].references[0], "BusinessRequirements")

            summaries = [event.summary for event in events]
            self.assertIn("Pipeline execution started", summaries)
            self.assertIn("Pipeline execution completed", summaries)

    def test_operational_logs_and_events_do_not_include_input_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_config(root)
            canary = "unique_canary_input_xyz123"
            stderr_capture = io.StringIO()

            with redirect_stderr(stderr_capture):
                pipeline_logger = setup_pipeline_logging(log_level="ERROR", verbose=False)
                logger = pipeline_logger.get_logger("test_collaboration")
                pipeline = Pipeline(config_root=str(root), dry_run=True)
                pipeline.set_logger(logger)
                result = pipeline.run_pipeline(canary, f"{temp_dir}/input.txt")

            stderr_output = stderr_capture.getvalue()
            self.assertNotIn(canary, stderr_output)

            events_path = (
                root / "runs" / result["run_id"] / "collaboration" / "collaboration_events.jsonl"
            )
            self.assertTrue(events_path.exists())
            events_payload = events_path.read_text(encoding="utf-8")
            self.assertNotIn(canary, events_payload)


class TestSchemaExport(unittest.TestCase):
    """Schema export coverage tests for collaboration events."""

    def test_export_contains_collaboration_event_schema(self):
        export_schemas.main()
        schema_path = Path("agentic/collaboration/schemas/CollaborationEvent.schema.json")
        self.assertTrue(schema_path.exists())
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema.get("title"), "CollaborationEvent")


if __name__ == "__main__":
    unittest.main()


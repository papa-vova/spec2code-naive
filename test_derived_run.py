"""Tests for amendment and derived run logic."""

import json
import tempfile
import unittest
from pathlib import Path

from agentic.artifacts.models import AmendmentContent, ArtifactType
from agentic.artifacts.store import ArtifactStore
from agentic.orchestration.derived_run import (
    apply_amendment,
    load_amendment,
    load_base_run_metadata,
)


class TestAmendmentContent(unittest.TestCase):
    """Tests for AmendmentContent model."""

    def test_minimal_amendment(self):
        content = AmendmentContent(base_run_id="run_123")
        self.assertEqual(content.base_run_id, "run_123")
        self.assertEqual(content.amended_assumptions, [])
        self.assertEqual(content.amended_tradeoffs, [])

    def test_full_amendment(self):
        content = AmendmentContent(
            base_run_id="run_123",
            amended_assumptions=[{"id": "ASM-0001", "description": "x", "status": "confirmed"}],
            amended_tradeoffs=[{"id": "TO-0001", "options": ["A"], "rationale": "y"}],
            reason="test",
        )
        self.assertEqual(len(content.amended_assumptions), 1)
        self.assertEqual(len(content.amended_tradeoffs), 1)


class TestLoadAmendment(unittest.TestCase):
    """Tests for load_amendment."""

    def test_load_valid_amendment(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"base_run_id": "run_1", "amended_assumptions": []}, f)
            path = f.name
        try:
            data = load_amendment(path)
            self.assertEqual(data["base_run_id"], "run_1")
        finally:
            Path(path).unlink()

    def test_missing_base_run_id_raises(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"amended_assumptions": []}, f)
            path = f.name
        try:
            with self.assertRaises(ValueError) as ctx:
                load_amendment(path)
            self.assertIn("base_run_id", str(ctx.exception))
        finally:
            Path(path).unlink()


class TestApplyAmendment(unittest.TestCase):
    """Tests for apply_amendment."""

    def test_merges_amended_context(self):
        base = {"pipeline_input": {"content": "x", "source": "f", "size": 1}}
        amendment = {
            "base_run_id": "r1",
            "amended_assumptions": [{"id": "ASM-001"}],
            "amended_tradeoffs": [],
        }
        result = apply_amendment(base, amendment)
        self.assertIn("amended_context", result)
        self.assertEqual(result["amended_context"]["amended_assumptions"], [{"id": "ASM-001"}])

    def test_missing_pipeline_input_raises(self):
        base = {}
        amendment = {"base_run_id": "r1"}
        with self.assertRaises(ValueError) as ctx:
            apply_amendment(base, amendment)
        self.assertIn("pipeline_input", str(ctx.exception))


class TestDerivedRunIntegration(unittest.TestCase):
    """Integration tests for derived run flow."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = ArtifactStore(runs_directory=self.tmp, create_artifacts=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_load_base_run_metadata(self):
        run_id = self.store.generate_run_id()
        self.store.initialize_run(run_id)
        metadata_path = self.store.get_run_directory(run_id) / "metadata.json"
        metadata = {
            "run_id": run_id,
            "pipeline_input": {"content": "test", "source": "x", "size": 4},
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f)
        loaded = load_base_run_metadata(self.store, run_id)
        self.assertEqual(loaded["run_id"], run_id)
        self.assertIn("pipeline_input", loaded)

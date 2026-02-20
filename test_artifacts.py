#!/usr/bin/env python3
"""Tests for canonical artifact models, store, validation, and integration."""

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import yaml

from agentic.artifacts.models import (
    Artifact,
    ArtifactIdentity,
    ArtifactProvenance,
    ArtifactType,
    ModelConfigRef,
    PromptRef,
    compute_content_hash,
)
from agentic.artifacts.registry import ARTIFACT_CONTENT_MODELS, get_content_model
from agentic.artifacts.store import ArtifactStore
from agentic.artifacts.validation import validate_content, validate_envelope
from config_system.agent_factory import AgentFactory, ModelRegistry
from config_system.config_loader import ConfigLoader
from main import Pipeline


class TestArtifactModels(unittest.TestCase):
    """Model and registry behavior tests."""

    def test_content_hash_is_deterministic(self):
        content_a = {"b": 2, "a": 1}
        content_b = {"a": 1, "b": 2}
        self.assertEqual(compute_content_hash(content_a), compute_content_hash(content_b))
        self.assertTrue(compute_content_hash(content_a).startswith("sha256:"))

    def test_registry_covers_all_artifact_types(self):
        self.assertEqual(set(ARTIFACT_CONTENT_MODELS.keys()), set(ArtifactType))
        for artifact_type in ArtifactType:
            self.assertTrue(get_content_model(artifact_type))

    def test_validate_envelope_and_content(self):
        artifact = Artifact(
            identity=ArtifactIdentity(
                artifact_id="BusinessRequirements",
                artifact_type=ArtifactType.BUSINESS_REQUIREMENTS,
                schema_version="1.0.0",
            ),
            provenance=ArtifactProvenance(
                run_id="run1",
                created_at="2026-02-19T14:30:00+00:00",
                created_by_role="business_analyst",
                created_by_agent_instance_id="a1",
                model_config_ref=ModelConfigRef(
                    provider="OpenAI", model_name="gpt-5-mini", parameters={}
                ),
                role_model_profile_id="business_analyst",
                prompt_ref=PromptRef(template_name="default", template_version="v1"),
            ),
            content={"title": "T", "functional_requirements": []},
            content_hash=compute_content_hash({"title": "T", "functional_requirements": []}),
        )
        payload = artifact.model_dump(mode="json")
        self.assertEqual(validate_envelope(payload), [])
        self.assertEqual(
            validate_content(ArtifactType.BUSINESS_REQUIREMENTS, artifact.content),
            [],
        )

        broken_payload = dict(payload)
        del broken_payload["identity"]
        self.assertTrue(validate_envelope(broken_payload))


class TestArtifactStore(unittest.TestCase):
    """Artifact store filesystem and metadata tests."""

    def test_store_write_read_and_metadata_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ArtifactStore(runs_directory=temp_dir, create_artifacts=True)
            run_id = store.generate_run_id()
            store.initialize_run(run_id)

            content = {"title": "Example"}
            artifact = Artifact(
                identity=ArtifactIdentity(
                    artifact_id="BusinessRequirements",
                    artifact_type=ArtifactType.BUSINESS_REQUIREMENTS,
                    schema_version="1.0.0",
                ),
                provenance=ArtifactProvenance(
                    run_id=run_id,
                    created_at="2026-02-19T14:30:00+00:00",
                    created_by_role="business_analyst",
                    created_by_agent_instance_id="agent-instance",
                    model_config_ref=ModelConfigRef(
                        provider="OpenAI", model_name="gpt-5-mini", parameters={}
                    ),
                    role_model_profile_id="business_analyst",
                    prompt_ref=PromptRef(template_name="default", template_version="v1"),
                ),
                content=content,
                content_hash=compute_content_hash(content),
            )

            artifact_path = store.write_artifact(run_id, artifact)
            self.assertTrue(artifact_path.exists())

            loaded = store.read_artifact(run_id, "BusinessRequirements")
            self.assertEqual(loaded.content_hash, artifact.content_hash)

            metadata_path = store.write_metadata(
                run_id=run_id,
                config_root=temp_dir,
                input_file=f"{temp_dir}/input.txt",
                pipeline_name="test_pipeline",
                execution_successful=True,
                total_execution_time=5.0,
                artifacts_manifest=[
                    {
                        "artifact_type": "BusinessRequirements",
                        "file": "artifacts/BusinessRequirements.json",
                        "content_hash": artifact.content_hash,
                    }
                ],
            )
            self.assertTrue(metadata_path.exists())
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertIsNotNone(datetime.fromisoformat(metadata["timestamp"]).tzinfo)
            self.assertEqual(metadata["artifacts_manifest"][0]["artifact_type"], "BusinessRequirements")


class TestRoleProfilesAndIntegration(unittest.TestCase):
    """Role profile loading and dry-run integration tests."""

    def _write_minimal_config(self, root: Path):
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

    def test_role_profile_resolution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_config(root)
            loader = ConfigLoader(str(root))
            self.assertEqual(loader.get_role_model("test_role"), "test_model")

    def test_agent_factory_model_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_config(root)
            loader = ConfigLoader(str(root))
            factory = AgentFactory(loader)

            with patch.object(ModelRegistry, "create_llm", return_value=Mock(name="llm_mock")):
                agent = factory.create_agent_with_model("test_role", "test_model", dry_run=False)
                self.assertEqual(agent.config.name, "test_role")
                self.assertIsNotNone(agent.llm)

    def test_pipeline_dry_run_persists_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_config(root)
            pipeline = Pipeline(config_root=str(root), dry_run=True)
            result = pipeline.run_pipeline("hello world", f"{temp_dir}/input.txt")

            run_id = result["run_id"]
            artifact_path = root / "runs" / run_id / "artifacts" / "BusinessRequirements.json"
            self.assertTrue(artifact_path.exists())

            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual(validate_envelope(payload), [])


if __name__ == "__main__":
    unittest.main()


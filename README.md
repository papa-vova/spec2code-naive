# spec2code-naive

Multi-agent LangChain pipeline that transforms rough feature descriptions into formalized, auditable specification artifacts. Agents are configured via YAML and produce typed, schema-validated artifacts with full provenance.

## How It Works

- Agents execute sequentially as defined in `config/pipeline.yaml`.
- Each agent produces a **typed artifact** stored as a separate JSON file under `runs/<run_id>/artifacts/`.
- Every artifact carries an **envelope** (identity, provenance, quality metadata, content hash) validated at write time.
- **Per-role model profiles** in `config/agentic.yaml` control which LLM each role uses.
- Operational logs go to `stderr` (JSON, content-free); structured output goes to `stdout`.
- Exit codes: 0 = success, 1 = failure.

## Structure

```text
spec2code-naive/
  main.py                          # CLI entry point
  test_artifacts.py                # Artifact system tests
  test_collaboration.py            # Collaboration artifact tests
  test_runtime.py                  # Pipeline regression tests
  test_config.py                   # Config validation tool
  requirements.txt                 # Python dependencies
  sample_input.txt                 # Example input file
  logging_config.py                # Logging configuration
  exceptions.py                    # Custom exceptions
  agentic/
    artifacts/
      models.py                    # Artifact envelope + 18 content models
      registry.py                  # ArtifactType -> content model mapping
      store.py                     # ArtifactStore (run dirs, read/write)
      validation.py                # Envelope (hard gate) + content (soft gate)
      schemas/                     # Generated JSON Schema files (19 files)
    collaboration/
      models.py                    # Collaboration event models
      event_log.py                 # JSONL event log writer/reader
      transcript_store.py          # Stakeholder transcript/content store
      schemas/
        CollaborationEvent.schema.json
  core/
    agent.py                       # Agent execution (LangChain)
    orchestrator.py                # Pipeline orchestration + artifact wrapping
    run_manager.py                 # Deprecated; kept for reference
  config/
    agentic.yaml                   # Role model profiles
    pipeline.yaml                  # Agent sequence and inputs
    models/                        # LLM provider configs
      openai_gpt5.yaml
      openai_gpt5_mini.yaml
      openai_gpt5_nano.yaml
    agents/                        # Agent configs and prompts
      business_analyst/
      ba_lead/
      plan_maker/
      plan_critique_generator/
      plan_critique_comparator/
  config_system/
    config_loader.py               # Config loading, validation, agentic config
    agent_factory.py               # Agent instantiation with model override
  scripts/
    export_schemas.py              # Generate JSON Schema files from models
  runs/                            # Run output storage
    <run_id>/
      metadata.json                # Run metadata + artifacts manifest
      artifacts/
        BusinessRequirements.json  # Typed artifact with envelope
  docs/
    spec2code-naive raw initial plan.md
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install langchain-openai  # or preferred provider
export OPENAI_API_KEY="your-key"
```

## Usage

```bash
# Run pipeline
.venv/bin/python main.py -i sample_input.txt

# Dry run (no LLM calls)
.venv/bin/python main.py -i sample_input.txt --dry-run

# All options
.venv/bin/python main.py --help
```

## Testing

```bash
# Artifact system tests (models, store, validation, role profiles, integration)
.venv/bin/python -m unittest test_artifacts.py

# Collaboration artifact tests
.venv/bin/python -m unittest test_collaboration.py

# Pipeline regression tests
.venv/bin/python test_runtime.py

# Config validation
.venv/bin/python test_config.py validate

# Full regression gate
.venv/bin/python -m unittest test_artifacts.py \
  && .venv/bin/python -m unittest test_collaboration.py \
  && .venv/bin/python test_runtime.py \
  && .venv/bin/python test_config.py validate
```

## Regenerating JSON Schemas

```bash
.venv/bin/python scripts/export_schemas.py
```

Schemas are written to `agentic/artifacts/schemas/` and `agentic/collaboration/schemas/` and should be checked into the repo.

## Configuration

See [config/README.md](config/README.md) for agent/model configuration details.

### Role Model Profiles

`config/agentic.yaml` maps each role to a model config:

```yaml
role_model_profiles:
  business_analyst:
    model: openai_gpt5
  qa_engineer:
    model: openai_gpt5_mini
```

The orchestrator resolves the model per role at runtime and records it in artifact provenance.

## Run System And Artifact Store

### Run Folder Layout

```text
runs/<run_id>/
  metadata.json
  artifacts/
    BusinessRequirements.json
    ...
  collaboration/
    collaboration_events.jsonl
    stakeholder_transcript.txt
```

### Metadata File

```json
{
  "run_id": "20260220_093000_abc12345",
  "timestamp": "2026-02-20T09:30:00.000000+00:00",
  "pipeline_name": "requirements_generator_pipeline",
  "execution_successful": true,
  "total_execution_time": 10.5,
  "artifacts_manifest": [
    {
      "artifact_type": "BusinessRequirements",
      "file": "artifacts/BusinessRequirements.json",
      "content_hash": "sha256:abcdef..."
    }
  ]
}
```

### Artifact Envelope

Every artifact JSON follows this structure:

```json
{
  "identity": {
    "artifact_id": "BusinessRequirements",
    "artifact_type": "BusinessRequirements",
    "schema_version": "1.0.0"
  },
  "provenance": {
    "run_id": "...",
    "created_at": "2026-02-20T09:30:01.000000+00:00",
    "created_by_role": "business_analyst",
    "created_by_agent_instance_id": "uuid",
    "model_config_ref": { "provider": "OpenAI", "model_name": "gpt-5" },
    "role_model_profile_id": "business_analyst",
    "prompt_ref": { "template_name": "...", "template_version": "..." }
  },
  "content": { ... },
  "quality_metadata": {
    "assumptions": [],
    "open_questions": [],
    "risks": [],
    "acceptance_criteria": []
  },
  "content_hash": "sha256:..."
}
```

Envelope validation is a hard gate; content validation is warning-level during early milestones.

### Collaboration Artifacts

Milestone 2 introduces run-scoped collaboration artifacts:

- `collaboration_events.jsonl`: append-only event stream (`orchestrator_decision_made`, `artifact_produced`, and future stakeholder events).
- `stakeholder_transcript.txt`: plain-file transcript storage for Product Owner and stakeholder interaction content.
- Events store references and hashes; operational logs remain content-free.

## Architecture And Refactoring Plan

See [agentic_refactoring_plan.md](agentic_refactoring_plan.md) for the full agentic architecture blueprint and milestone roadmap.

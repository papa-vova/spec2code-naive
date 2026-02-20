# spec2code-naive

Multi-agent LangChain pipeline that transforms rough feature descriptions into formalized, auditable specification artifacts. Agents are configured via YAML and produce typed, schema-validated artifacts with full provenance.

## Current Implementation

- The orchestrator executes configured agents sequentially from `config/pipeline.yaml`.
- Each agent produces a **typed artifact** stored as a separate JSON file under `runs/<run_id>/artifacts/`.
- Every artifact carries an **envelope** (identity, provenance, quality metadata, content hash) validated at write time.
- **Per-role model profiles** in `config/agentic.yaml` control which LLM each role uses.
- **Provider-agnostic rate limit handling**: retries on 429 with header-based wait or exponential backoff.
- The orchestrator runs an information sufficiency gate and can stop runs below confidence threshold.
- Deterministic and semantic audit results are persisted under `runs/<run_id>/audits/audit_results.json`.
- Collaboration artifacts are stored separately under `runs/<run_id>/collaboration/`.
- Operational logs go to `stderr` (JSON, content-free).
- Exit codes: 0 = success, 1 = failure.

## Structure

```text
spec2code-naive/
  main.py                          # CLI entry point
  test_artifacts.py                # Artifact system tests
  test_collaboration.py            # Collaboration artifact tests
  test_audits.py                   # Audit gate and stop-logic tests
  test_rate_limit.py               # Rate limit retry tests
  test_derived_run.py              # Amendment and derived run tests
  test_performance_audits.py      # 3NF and performance guidance audit tests
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
      schemas/                     # Generated JSON Schema files (20 files)
    collaboration/
      models.py                    # Collaboration event models
      event_log.py                 # JSONL event log writer/reader
      transcript_store.py          # Stakeholder transcript/content store
      schemas/
        CollaborationEvent.schema.json
    audits/
      checks.py                    # Deterministic audit checks
      gates.py                     # Sufficiency + audit gate runners
      rubric_eval.py               # Semantic evaluator interface
      traceability.py              # Traceability matrix generator
    orchestration/
      derived_run.py               # Derived run and amendment handling
    runtime/
      rate_limit.py                # Rate limit retry (provider-agnostic)
  core/
    agent.py                       # Agent execution (LangChain)
    orchestrator.py                # Pipeline orchestration + artifact wrapping
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
      audits/
        audit_results.json         # Deterministic + semantic audit outputs
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

# Derived run (re-run with amendments from a base run)
.venv/bin/python main.py --base-run <run_id> --amendment-file amendment.json
.venv/bin/python main.py --base-run <run_id> --amendment-file amendment.json --dry-run

# All options
.venv/bin/python main.py --help
```

## Testing

```bash
# Artifact system tests (models, store, validation, role profiles, integration)
.venv/bin/python -m unittest test_artifacts.py

# Collaboration artifact tests
.venv/bin/python -m unittest test_collaboration.py

# Audit gate tests
.venv/bin/python -m unittest test_audits.py

# Rate limit tests
.venv/bin/python -m unittest test_rate_limit.py

# Amendment and derived run tests
.venv/bin/python -m unittest test_derived_run.py

# Performance and data model audit tests
.venv/bin/python -m unittest test_performance_audits.py

# Pipeline regression tests
.venv/bin/python test_runtime.py

# Config validation
.venv/bin/python test_config.py validate

# Full regression gate
.venv/bin/python -m unittest test_artifacts.py \
  && .venv/bin/python -m unittest test_collaboration.py \
  && .venv/bin/python -m unittest test_audits.py \
  && .venv/bin/python -m unittest test_rate_limit.py \
  && .venv/bin/python -m unittest test_derived_run.py \
  && .venv/bin/python -m unittest test_performance_audits.py \
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

### Rate Limiting

`config/agentic.yaml` can include a `rate_limit` section for LLM retry behavior:

```yaml
rate_limit:
  max_retries: 6
  initial_delay: 1.0
  exponential_base: 2.0
  use_header_reset: true
  reset_header_names:
    - x-ratelimit-reset-requests
    - x-ratelimit-reset-tokens
    - retry-after
```

On 429 (rate limit), the system waits using header-based reset time when available, else exponential backoff. Provider-agnostic: works with any LLM API that returns 429 and standard headers.

### Derived Runs

A derived run re-executes the pipeline from a base run with amendments:

```bash
.venv/bin/python main.py --base-run <base_run_id> --amendment-file amendment.json
```

Amendment JSON format:

```json
{
  "base_run_id": "<run_id>",
  "amended_assumptions": [{"id": "ASM-0001", "description": "...", "status": "..."}],
  "amended_tradeoffs": [{"id": "TO-0001", "options": [...], "rationale": "..."}],
  "reason": "Optional reason for amendment"
}
```

All new artifacts from a derived run have `provenance.base_run_id` set. The base run must have `pipeline_input` stored in metadata (runs created with this version).

### Performance And Data Model Audits

When `ImplementationDesign` is produced, optional audits enforce 3NF and performance guidance:

```yaml
audit:
  require_3nf_data_structures: false
  require_performance_guidance: false
```

- `require_3nf_data_structures`: when true, `ImplementationDesign` must include at least one `data_structures` entry; non-3NF entries require `denormalization_rationale`.
- `require_performance_guidance`: when true, `ImplementationDesign` must include `performance_guidance` entries or module-level `complexity` (Big-O).

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
  audits/
    audit_results.json
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

Run-scoped collaboration artifacts:

- `collaboration_events.jsonl`: append-only event stream (`orchestrator_decision_made`, `artifact_produced`, and future stakeholder events).
- `stakeholder_transcript.txt`: plain-file transcript storage for Product Owner and stakeholder interaction content.
- Events store references and hashes; operational logs remain content-free.

### Audit Gates And Stop Logic

Audit-driven orchestration controls:

- `InfoSufficiencyAssessment` is generated at intake with `confidence_score` and `blocking_gaps`.
- Confidence threshold is configurable in `config/agentic.yaml` via `audit.min_confidence_to_proceed`.
- Runs stop early when confidence is below threshold and surface required additional inputs.
- `TraceabilityMatrix` is generated as a canonical artifact.
- `audits/audit_results.json` stores deterministic and semantic gate outcomes.

### Derived Runs

- `--base-run` and `--amendment-file` trigger a derived run.
- Pipeline input is replayed from base run metadata; amendments are merged into `amended_context`.
- All artifacts carry `provenance.base_run_id` for traceability.

## Architecture

### Overview

Role-based workflow: product -> requirements -> architecture -> implementation -> review. The Product Owner is the only human-facing role; other roles run automatically on artifacts.

### Core Roles And Artifacts

| Role | Output artifacts |
|------|------------------|
| Product Owner | `ProblemBrief` |
| Business Analyst | `BusinessRequirements`, `NonFunctionalRequirements` |
| Solution Architect | `C4Model`, `ArchitectureDecisionRecordSet`, `TechStackRecommendation` |
| System Analyst | `ImplementableSpec` |
| Developer | `ImplementationDesign`, `WorkBreakdown` |
| Senior Developer | `DesignReview`, `CodeReview` |
| Security/Privacy Reviewer | `ThreatModel`, `PrivacyChecklist` |
| QA / Test Engineer | `TestPlan`, `AcceptanceTests` |

### Assumptions, Trade-Offs, Amendments

- `AssumptionLedger`: stable IDs (`ASM-*`), links to impacted requirements.
- `TradeoffRegister`: stable IDs (`TO-*`), options, rationale.
- `Amendment`: references `base_run_id`; triggers derived run that recomputes dependent artifacts.

### Data Modeling And Performance

- **3NF**: Persistent data models must be at least 3NF. Deliberate denormalization requires explicit rationale.
- **ImplementationDesign** must include `data_structures` (with `normalization_level`) and `performance_guidance` (complexity, indexing, cardinality, hot paths) when the corresponding audit flags are enabled.

### Log Separation

- **Operational logs**: stderr, JSON, content-free (IDs, hashes, counts only).
- **Collaboration artifacts**: full content in `runs/<run_id>/collaboration/` (events, transcript).

### Conventions

- Stable IDs: `REQ-0001`, `ADR-0001`, `ASM-0001`, etc.
- Architecture: C4-PlantUML.
- Timestamps: RFC 3339 (UTC).

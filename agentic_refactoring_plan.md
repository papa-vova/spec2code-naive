# Agentic Refactoring Plan (Spec2Code)

## Context And Current Baseline

This repository is already a multi-agent pipeline:

- Agents run **sequentially** as defined in YAML (`config/pipeline.yaml`).
- Agents and prompts are configured in `config/agents/**`.
- A run produces artifacts in `runs/<run_id>/` (for example `result.json`, `metadata.json`).
- Operational logs go to **stderr**; pipeline output goes to **stdout**.

The refactor goal is to evolve this from a static, linear “pipeline of agents” into a **fully agentic architecture** where a single orchestrator can:

- Decide **which role** to run next.
- Spawn **multiple instances** of roles when useful (diversity / debate / parallel alternatives).
- Iterate by requesting the **Product Owner** to obtain missing stakeholder details (the orchestrator and other roles do not interact with the human directly).
- Produce **typed, auditable artifacts** with explicit provenance and consistency checks.

## Goals, Non-Goals, And Key Tensions

### Goals

- **Role-based workflow**: product → requirements → architecture → implementation design → review.
- **Human-in-the-loop (Product Owner only)**: only the Product Owner interacts with the stakeholder; the rest of the system consumes and produces artifacts.
- **Auditability**: every output is attributable to inputs, prompts, role policy, and prior artifacts.
- **Consistency**: automatic checks catch contradictions and missing coverage across artifacts.
- **Reproducibility**: a run can be replayed or resumed from saved state.
- **Separation of logs**:
  - **Operational logs** (stderr): safe, structured, no user/content text.
  - **Collaboration artifacts**: a separate run store for stakeholder transcript and decision records (business artifacts, not technical logs).

### Non-Goals (For This Refactor)

- Not a full project-management system (sprints, assignments, calendars).
- Not an IDE plugin (though the architecture should allow one later).
- Not a “single perfect spec generator”; the design assumes iteration, uncertainty, and controlled amendments.

### Key Tensions And How To Handle Them

- **Dynamic orchestration vs reproducibility**: dynamic decisions are allowed, but must be recorded as first-class run events (inputs, outputs, policy/rubric used, and the chosen branch).
- **Collaboration artifacts vs operational safety**: operational logs must remain content-free; stakeholder interaction content lives in separate collaboration artifacts.

## Proposed Roles (Challenged And Improved)

Your role set is a good start. The main improvement is to make outputs and boundaries explicit and to reduce semantic overlap between “business analyst” and “system analyst”.

### Core Roles (Recommended)

- **Product Owner (PO) / Product Manager**
  - **Purpose**: elicit missing context from a moderately tech-savvy stakeholder.
  - **Interaction**: must support interactive Q&A with the human.
  - **Output artifact**: `ProblemBrief` (improved initial formulation + success criteria + constraints + assumptions + glossary).

- **Business Analyst (BA)**
  - **Purpose**: translate business goals into measurable requirements and constraints.
  - **Interaction**: collaborates with PO; may request additional clarifications via PO when necessary.
  - **Output artifacts**: `BusinessRequirements` and `NonFunctionalRequirements`.

- **Solution Architect (SA)**
  - **Purpose**: propose architecture options and select a recommended approach.
  - **Output artifacts**:
    - `ArchitectureDecisionRecordSet` (ADRs with trade-offs)
    - `C4Model` (C4-PlantUML source and identifiers)
    - `TechStackRecommendation`

- **System Analyst (SysA) / Requirements Engineer**
  - **Purpose**: convert BA+SA outputs into implementation-ready requirements.
  - **Key improvement**: this role should produce a **single canonical “implementable spec”** with stable identifiers.
  - **Output artifact**: `ImplementableSpec` (functional requirements, NFRs, data contracts, acceptance criteria, edge cases).

- **Developer**
  - **Purpose**: produce a formalized implementation design and plan that is grounded in the `ImplementableSpec`.
  - **Output artifacts**:
    - `ImplementationDesign` (modules, algorithms, key data structures, API design, migrations)
    - `WorkBreakdown` (tasks linked to requirement IDs; test approach; rollout plan)

- **Senior Developer (Reviewer)**
  - **Purpose**: design review and code review (and “review of review” if using multiple dev instances).
  - **Output artifacts**:
    - `DesignReview` (findings, required changes, optional improvements)
    - `CodeReview` (if/when code exists)

- **Security/Privacy Reviewer**
  - **Purpose**: threat model, data classification, privacy constraints for collaboration artifacts and runtime behaviors.
  - **Output artifact**: `ThreatModel` and `PrivacyChecklist`.

- **QA / Test Engineer**
  - **Purpose**: independent test strategy and acceptance test cases.
  - **Output artifact**: `TestPlan` and `AcceptanceTests`.

Rationale: these two roles materially improve “automatically auditable correctness” because they provide independent rubrics and structured acceptance tests.

## Orchestrator Design (Single Technical Project Manager)

### Orchestrator Responsibilities

The orchestrator (technical PM) is the only component allowed to:

- Select the next role(s) to run.
- Decide whether the process must stop due to insufficient information (based on a configurable confidence threshold).
- Decide when to request that the **Product Owner** obtains additional stakeholder input (only the Product Owner interacts with the human directly).
- Decide how many parallel instances to spawn (for diversity).
- Decide when an artifact is “good enough” to proceed or must be revised.
- Enforce policies: budgets, per-role model selection, artifact schemas, and audit gates.

### Orchestrator Operating Model

Use an explicit **state machine** with gates. A minimal set:

- `Intake` → `Clarify` → `Requirements` → `Architecture` → `ImplementableSpec` → `ImplementationDesign` → `Review` → `Final`

Each transition is guarded by an **audit gate** (see “Auditing And Consistency”).

### Information Sufficiency And Confidence (Stop Condition)

The orchestrator must run an explicit **information sufficiency evaluation** after `Clarify` (and optionally after later steps). This produces an `InfoSufficiencyAssessment` artifact with:

- **Coverage**: which required areas are sufficiently specified (per a rubric).
- **Confidence score**: a numeric score in \([0, 1]\), plus per-area sub-scores.
- **Blocking gaps**: missing inputs that prevent safe progression.

Policy:

- Deterministic checks must pass (schemas, references), but they do not determine sufficiency.
- A configurable threshold (for example `MIN_CONFIDENCE_TO_PROCEED`) controls whether the orchestrator proceeds or halts and requests additional stakeholder input via the Product Owner.

### Multi-Instance Strategy (When To Spawn Multiple Agents)

Spawn multiple instances when:

- There is uncertainty (many open questions; high ambiguity).
- There are important trade-offs (architecture or algorithm choice).
- You need robust checking (review, security, test planning).

Recommended patterns:

- **Generate-and-critique**: one generator + one critic per artifact.
- **N-way alternatives**: produce 2–3 architecture options, then select via rubric.
- **Debate then synthesize**: conflicting proposals resolved into a single canonical artifact by the orchestrator.

### Prompt Amendment And Policy Control

Prompt changes are allowed, but must be treated as a **recorded decision**:

- Every role invocation saves:
  - prompt template version
  - parameterization
  - policy/rubric used for evaluation
  - reason for amendment (in controlled vocabulary)

This is required for auditability and replay.

## Stakeholder Interaction (Only Product Owner) And Amendment Loop

### Stakeholder Interaction Contract

- Only the **Product Owner** can ask questions to and receive answers from the human stakeholder.
- All other roles operate only on artifacts produced within the run.

### Capturing Assumptions And Trade-Offs

Assumptions and trade-offs must be first-class, versioned artifacts:

- `AssumptionLedger`
  - Stable assumption IDs (`ASM-*`)
  - Status: proposed / accepted / rejected / amended
  - Impacted requirement IDs (`REQ-*`) and decisions (`ADR-*`)
- `TradeoffRegister`
  - Stable trade-off IDs (`TO-*`)
  - Options considered, selection rationale, and “what would change our mind”
  - Links to NFR conflicts and associated ADRs

### Formal Amendments And Derived Reruns (Rehash Dependent Artifacts)

To update assumptions/trade-offs and recompute the artifact set:

- Introduce an `Amendment` artifact:
  - References the prior run (`base_run_id`) and the specific items amended (`ASM-*`, `TO-*`, `REQ-*`).
  - Records the stakeholder change request as structured deltas.
- The orchestrator starts a **derived run** that:
  - Reuses unchanged artifacts by reference (content hash) where allowed by policy.
  - Recomputes all dependent artifacts and produces new hashes and provenance.

This enables repeatable “relaunch with formalized amendments” without manual ad-hoc edits.

## Artifacts: Types, Canonical Format, And Provenance

### Design Principle

Treat every produced document as a **typed artifact** with machine-validated structure. Human-readable formatting is a view of the artifact, not the source of truth.

### Canonical Artifact Format

Canonical format should be JSON (or YAML) with a strict schema per artifact type.

Each artifact should include:

- **Identity**
  - `artifact_id` (stable within a run)
  - `artifact_type`
  - `artifact_version` (schema version)
- **Provenance**
  - `run_id`
  - `created_by_role`
  - `created_by_agent_instance_id`
  - `inputs` (references to prior artifact IDs + content hashes)
  - `model_config_ref` (provider/model + settings; no secrets)
  - `role_model_profile_id` (role-specific model selection, configured and recorded per role)
  - `prompt_ref` (template + revision)
- **Content**
  - typed fields, not freeform blobs
  - requirement IDs must be stable and referenced across artifacts
- **Quality Metadata**
  - `assumptions`
  - `open_questions`
  - `risks`
  - `acceptance_criteria`

### Artifact Store Layout (Within A Run)

Extend the current `runs/<run_id>/` layout into a predictable structure:

```text
runs/<run_id>/
  metadata.json
  artifacts/
    ProblemBrief.json
    BusinessRequirements.json
    NonFunctionalRequirements.json
    C4Model.json
    ArchitectureDecisionRecordSet.json
    AssumptionLedger.json
    TradeoffRegister.json
    InfoSufficiencyAssessment.json
    ImplementableSpec.json
    ImplementationDesign.json
    WorkBreakdown.json
    DesignReview.json
    ThreatModel.json
    PrivacyChecklist.json
    TestPlan.json
    AcceptanceTests.json
  collaboration/
    stakeholder_transcript.txt
    collaboration_events.jsonl
  audits/
    audit_results.json
```

## Auditing And Consistency (Automatically Auditable)

### Audit Gates (Run-Level)

Before moving to the next state, the orchestrator runs audits and stores results in `audits/audit_results.json`.

Suggested required gates:

- **Schema validation**: every artifact must validate against its schema.
- **Traceability validation**:
  - every implementable requirement traces back to a business objective
  - every implementation task traces to requirement IDs
- **Consistency validation**:
  - no contradictory NFRs (for example latency vs cost) without explicit trade-off ADR
  - architecture addresses required NFR categories (availability, security, observability, scalability, privacy)
- **Completeness checks**:
  - no “TBD” fields in required sections
  - all open questions either answered or explicitly deferred with impact assessment

### Audit Methods (Layered)

- **Deterministic checks** (preferred): schema, ID references, missing fields, duplicates, coverage counts.
- **Rubric-based evaluation** (LLM-assisted): for semantic checks like “does architecture address NFR X”.
  - The rubric itself must be versioned and stored as an artifact or config.
  - The evaluator output must cite evidence by artifact references and section pointers.

Orchestrator policy:

- Deterministic checks must always hold (hard gate).
- Semantic checks are more important for orchestration decisions (they drive “proceed / revise / stop”, confidence scoring, and role routing).

### Traceability Matrix (Recommended Artifact)

Add a generated `TraceabilityMatrix` artifact:

- Rows: implementable requirements (`REQ-*`)
- Columns: business objectives (`OBJ-*`), architecture decisions (`ADR-*`), design elements (`DES-*`), tasks (`TASK-*`), tests (`TEST-*`)
- Cells: references; empty cells highlight gaps.

This artifact is a cornerstone for “automatically auditable correctness”.

## Collaboration Artifacts (Not Technical Logs)

### Separation Of Concerns

- **Operational logs**: stderr JSON logs; must contain no business content (only IDs/hashes, timings, counts).
- **Collaboration artifacts**: stored under `runs/<run_id>/collaboration/`; these are business artifacts used for auditing and traceability.

### Collaboration Event Model

Store as append-only JSONL with events such as:

- `stakeholder_question_asked` (Product Owner only)
- `stakeholder_answer_received` (Product Owner only)
- `artifact_produced`
- `artifact_revised`
- `audit_gate_passed` / `audit_gate_failed`
- `orchestrator_decision_made`

Each event should include:

- `event_id`, `timestamp`, `run_id`
- `actor` (role or human)
- `references` (artifact IDs, audit IDs)
- `content_ref` (pointer to a separate content blob when needed)

### Full Stakeholder Content Storage

Store full stakeholder interaction content separately as plain files (for now), and reference it from events and artifacts by path plus content hash.

## Target Codebase Architecture (Clean, Agentic, Testable)

### Guiding Principles

- Keep the current CLI and run system concepts, but separate:
  - orchestration policy
  - role execution runtime
  - artifact schemas and validators
  - audit gates
  - providers (LLMs, tools)

### Proposed Package Layout

This is a proposed end state; an incremental migration plan is below.

```text
./
  main.py
  logging_config.py
  exceptions.py
  core/                       # (kept temporarily; later slim or renamed)
  config_system/              # (kept temporarily; later slim or renamed)
  agentic/
    orchestration/
      orchestrator.py         # state machine + policy engine
      policies.py             # role routing, budgets, spawn rules
    roles/
      product_owner.py
      business_analyst.py
      solution_architect.py
      system_analyst.py
      developer.py
      senior_developer.py
      security_reviewer.py
      qa_engineer.py
    artifacts/
      models.py               # typed models for artifacts
      schemas/                # JSON Schemas or pydantic-based validators
      store.py                # read/write artifact store
    audits/
      gates.py                # audit gates + orchestration hooks
      checks.py               # deterministic validators
      rubric_eval.py          # evaluator interface
    collaboration/
      event_log.py            # collaboration event writer/reader
    runtime/
      agent_runner.py         # LLM invocation, tool calling, retries
      prompt_registry.py      # prompt templates and revisions
  config/
    agentic.yaml              # orchestrator policy + role configs
    roles/                    # per-role prompt templates and rubrics
    models/                   # provider configs
```

Note: The exact top-level package name can match your preference; the goal is clean separation, not the specific naming.

### Mapping From Current Modules (Suggested)

This keeps migration concrete and avoids a “big bang” rewrite:

- `core/orchestrator.py` → `agentic/orchestration/orchestrator.py` (state machine + routing)
- `core/agent.py` → `agentic/runtime/agent_runner.py` (role execution runtime)
- `core/run_manager.py` → `agentic/artifacts/store.py` (artifact store + run folders)
- `config_system/config_loader.py` → `agentic/runtime/prompt_registry.py` (prompt/rubric loading) and `agentic/orchestration/policies.py` (policy config loading)
- `config_system/agent_factory.py` → `agentic/runtime/agent_runner.py` (provider/model instantiation boundary)

## Migration Plan (No Backward Compatibility)

The target is a clean cutover to agentic orchestration. The migration can still be staged, but the “supported product” is the agentic orchestrator (no “pipeline mode”).

### Milestone 1: Canonical Artifacts, Schemas, And Role Model Profiles

- Define artifact type registry and schemas.
- Store artifacts as separate files under `runs/<run_id>/artifacts/`.
- Add **per-role model profiles** in config (each role selects its own model and parameters).

Exit criteria:

- A run produces the canonical artifacts and passes schema validation.

### Milestone 2: Collaboration Artifacts And Stakeholder Transcript

- Add collaboration events and a stakeholder transcript store (Product Owner only).
- Ensure operational logs remain content-free (IDs/hashes only).

Exit criteria:

- Stakeholder Q&A is traceable via collaboration artifacts and references to resulting artifacts.

### Milestone 3: Semantic-Driven Audits, Confidence, And Stop Logic

- Implement deterministic audits and the `TraceabilityMatrix` artifact.
- Add rubric-based semantic audits that drive orchestrator decisions.
- Add `InfoSufficiencyAssessment` with configurable confidence thresholds.

Exit criteria:

- The orchestrator stops when information is insufficient and can explain which additional stakeholder inputs are required.

### Milestone 4: Assumptions/Trade-Offs Amendment Loop And Derived Runs

- Add `AssumptionLedger`, `TradeoffRegister`, and `Amendment` artifacts.
- Support derived runs that rehash dependent artifacts after amendments.

Exit criteria:

- A formal amendment triggers a derived run that deterministically recomputes dependent artifacts with updated hashes and provenance.

### Milestone 5: Performance And Data Model Quality Gates (3NF + Indexing)

- Add explicit audits for:
  - 3NF compliance for persistent data models (or an ADR justifying deliberate denormalization)
  - performance expectations and indexing recommendations
- Ensure `ImplementationDesign` includes complexity analysis for critical flows.

Exit criteria:

- Produced designs include explicit 3NF data structures and performance guidance, and reviewers enforce them.

## Acceptance Criteria (Definition Of Done For The Refactor)

- A single command/run produces:
  - canonical typed artifacts per role
  - collaboration artifacts (stakeholder transcript + collaboration events)
  - audit results (including traceability)
- The orchestrator:
  - routes between roles dynamically
  - records every decision and prompt revision in run artifacts
  - can resume from a partially completed run
- Auditability:
  - schema validation passes
  - traceability matrix has no critical gaps (configurable threshold)
  - “review” artifacts explicitly cite evidence in earlier artifacts

## Data Modeling (3NF) And Performance Requirements

### Data Structures Must Be In 3NF

Any persistent data model described in `ImplementableSpec` and `ImplementationDesign` must be at least **third normal form (3NF)**:

- Each non-key attribute depends on the key, the whole key, and nothing but the key.
- No transitive dependencies in a table.
- Junction tables for many-to-many relationships.

Allowed exception:

- Deliberate denormalization is permitted only if:
  - documented as an ADR in `ArchitectureDecisionRecordSet`, and
  - paired with a correctness strategy (source of truth, sync rules), and
  - justified by measured or expected performance needs.

### Performance Guidance Must Be Produced

For every critical user/business flow, artifacts must include:

- **Complexity expectations**: dominant time/space complexity (Big-O) for core algorithms/queries.
- **Indexing recommendations**: proposed indexes and rationale (for example, composite indexes for common filter+sort patterns).
- **Cardinality and growth assumptions**: inputs to performance reasoning (linked to `AssumptionLedger`).
- **Hot paths**: identify highest-cost operations and recommended mitigations (batching, pagination, caching boundaries).

This is validated by semantic review (primary) and deterministic checks (presence and linkage).

## C4 Architecture (PlantUML Only)

Architecture representation is restricted to **C4 diagrams expressed as PlantUML**:

- `C4Model` should include:
  - `plantuml_source` (or referenced `.puml` files as run artifacts)
  - diagram list: context, container, component (as needed)
  - stable element identifiers used for traceability (`C4-*`)

## Open Decisions (Updated)

### Artifact Schema Technology (JSON Schema vs Pydantic)

Both can work; the main trade-off is portability vs developer ergonomics.

- **JSON Schema**
  - **Pros**: highly portable across languages/tools; easy to publish; good for long-term artifact compatibility; works well with “artifact store” approaches.
  - **Cons**: more boilerplate; weaker runtime ergonomics in Python; expressing some invariants can be awkward (cross-field constraints, rich typing).
- **Pydantic models**
  - **Pros**: excellent developer ergonomics in Python; strong typing; great error messages; easy cross-field validation; simpler to evolve while coding.
  - **Cons**: less language-portable as the “source of truth” (though you can export schemas); versioning and strict compatibility needs discipline; non-Python consumers prefer JSON Schema directly.

Offer (human readability + portability first):

- Use **JSON Schema as the canonical contract** for stored artifacts.
- Use **Pydantic as an internal implementation layer** to keep development fast.

### Stable ID Format (Offer)

Use short, human-friendly, prefix-based IDs with fixed-width counters, stable within a run and stable across derived runs unless the entity is conceptually replaced:

- Objectives: `OBJ-0001`
- Functional requirements: `REQ-0001`
- Non-functional requirements: `NFR-0001`
- Assumptions: `ASM-0001`
- Trade-offs: `TO-0001`
- Architecture decisions: `ADR-0001`
- Design elements: `DES-0001`
- Tasks: `TASK-0001`
- Tests: `TEST-0001`
- C4 elements: `C4-0001`

Rule:

- Revisions keep the same ID and increment an internal `revision` field.
- If an item is split/merged/replaced, record that relationship explicitly (`supersedes`, `derived_from`).

### “Redaction Strategy” Clarification

In this architecture:

- **Technical logs** (stderr) must never contain business/user content, only IDs/hashes and operational telemetry.
- **Collaboration artifacts** are business artifacts; they may contain full stakeholder content and are stored separately under `runs/<run_id>/collaboration/`.

No redaction is required for collaboration artifacts by default in this plan; access control and hygiene are handled outside the scope here.

### Full Interaction Content Storage

Store full stakeholder interaction content separately as plain files (for now). Reference it from:

- `AssumptionLedger` items (which question/answer introduced it)
- `Amendment` deltas (which stakeholder update changed it)
- collaboration events (path + hash)


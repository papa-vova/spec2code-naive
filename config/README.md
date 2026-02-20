# Configuration System Guide

This directory contains all configuration files for the pipeline system.

## Configuration Architecture

```text
config/
  agentic.yaml           # Role model profiles, rate limit, audit policy
  pipeline.yaml          # Pipeline orchestration and agent sequence
  models/                # Model provider configurations
    openai_gpt5.yaml
    openai_gpt5_mini.yaml
  agents/                # Agent-specific configurations
    business_analyst/
      agent.yaml         # Agent metadata and model reference
      prompts.yaml       # Prompt templates and system messages
```

## Agentic Configuration (`agentic.yaml`)

Central configuration for role model profiles, rate limit retry policy, and audit gates.

**Structure:**

```yaml
role_model_profiles:
  <role_name>:
    model: <model_config_name>

rate_limit:
  max_retries: 6
  initial_delay: 1.0
  exponential_base: 2.0
  use_header_reset: true
  reset_header_names:
    - x-ratelimit-reset-requests
    - x-ratelimit-reset-tokens
    - retry-after

audit:
  min_confidence_to_proceed: 0.6
  min_input_size_for_sufficiency: 120
  insufficient_markers: [TBD, TODO]
  sufficiency_rubric: null
  require_3nf_data_structures: false
  require_performance_guidance: false
```

**Parameters:**

- **`role_model_profiles`**: maps each role to a model config; the orchestrator resolves the model at runtime and overrides the agent-level `llm` setting
- **`rate_limit`**: provider-agnostic retry behavior for 429 responses
- **`audit`**: sufficiency and data model quality gate configuration

## Pipeline Configuration (`pipeline.yaml`)

Defines the agent execution sequence and pipeline-level settings.

**Structure:**

```yaml
pipeline:
  name: "pipeline_name"
  description: "Pipeline description"

  agents:
    - name: "agent_name"
      inputs: ["pipeline_input"]

  execution:
    mode: "sequential"

  settings:
    log_level: "INFO"
    create_run_artifacts: true
    include_messages_in_artifacts: false
    runs_directory: "runs"
```

**Parameters:**

- **`agents`**: list of agents to execute in sequence
  - **`name`**: must match a directory in `agents/`
  - **`inputs`**: `"pipeline_input"` for original input, or another agent name for chained input
  - **`prompt_templates`**: (optional) which prompt templates to use from the agent's prompts.yaml
- **`execution.mode`**: currently only `"sequential"`
- **`settings.log_level`**: `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`)
- **`settings.create_run_artifacts`**: whether to persist run artifacts (default: `true`)
- **`settings.include_messages_in_artifacts`**: capture LLM messages in artifacts (default: `false`)
- **`settings.runs_directory`**: output directory for runs (default: `runs/`)

## Model Configuration (`models/*.yaml`)

Defines LLM model providers, parameters, and credentials. The system uses dynamic provider discovery supporting any LangChain-compatible provider.

**Structure:**

```yaml
name: "model_identifier"
provider: "provider_name"
model_name: "specific_model"
parameters:
  temperature: 0.7
  max_tokens: 2000
  top_p: 1.0
  streaming: false
credentials:
  api_key: "${ENV_VAR}"
```

**Parameters:**

- **`name`**: unique identifier for this model configuration
- **`provider`**: LangChain provider name (e.g., `"OpenAI"`, case-sensitive for class lookup)
- **`model_name`**: specific model within the provider
- **`parameters`**: passed directly to the LLM constructor
- **`credentials`**: authentication parameters; `${VAR}` syntax expands environment variables

## Agent Configuration

Agent configuration consists of two files per agent.

### Agent Metadata (`agents/*/agent.yaml`)

```yaml
name: "agent_name"
description: "Agent purpose description"
llm: "model_config_name"
```

- **`name`**: agent identifier (should match directory name)
- **`description`**: human-readable purpose
- **`llm`**: reference to model config in `models/`; overridden at runtime by role model profile in `agentic.yaml`

### Prompt Configuration (`agents/*/prompts.yaml`)

```yaml
system_message: |
  System message defining the agent's role and behavior.

human_message_template: |
  Template for human messages with variables like {input}.

ai_message_prefix: |
  Optional prefix for AI responses.

prompt_templates:
  template_name: |
    Named template content with {input} variables.
```

**Parameters:**

- **`system_message`**: (required) system prompt defining agent role
- **`human_message_template`**: (required) template for human messages, supports `{input}` variable
- **`ai_message_prefix`**: (optional) prefix for AI responses
- **`prompt_templates`**: (optional) three valid formats:
  - **Missing/empty**: uses only `human_message_template`
  - **Single string**: actual template content (not a name reference)
  - **Dictionary**: named template variations for different scenarios

**Template variables:**

- **`{input}`**: the main input content (string representation of JSON if input is JSON)
- **Any JSON key**: if input is JSON, reference keys directly (e.g., `{title}`, `{description}`)

# Configuration System Guide

This directory contains all configuration files for the pipeline system. The configuration system supports multi-template execution without requiring code changes.

## Configuration Architecture

The system uses a hierarchical configuration structure:

```bash
config/
├── pipeline.yaml          # Pipeline orchestration and agent sequence
├── models/                # Model provider configurations
│   ├── openai_gpt4.yaml
│   ├── anthropic_claude.yaml
│   └── ollama_llama.yaml
└── agents/                # Agent-specific configurations
    ├── plan_maker/
    │   ├── agent.yaml     # Agent metadata and model reference
    │   └── prompts.yaml   # Prompt templates and system messages
    ├── plan_critique_generator/
    │   ├── agent.yaml
    │   └── prompts.yaml
    └── plan_critique_comparator/
        ├── agent.yaml
        └── prompts.yaml
```


## Pipeline Configuration (`pipeline.yaml`)

Defines the overall pipeline execution flow, agent sequence, and data mapping.

**Generic Structure:**
```yaml
pipeline:
  name: "pipeline_name"
  description: "Pipeline description"
  
  # Agent execution sequence
  agents:
    - name: "agent_name"              # Must match agent directory name
      input_sources: ["data_source"]   # Where this agent gets its input
  
  # Execution settings
  execution:
    mode: "sequential"               # Currently only sequential supported
    
  # Pipeline-level settings
  settings:
    log_level: "INFO"                        # DEBUG, INFO, WARNING, ERROR (default: INFO)
    create_run_artifacts: true               # Whether to create run artifacts (default: true)
    include_messages_in_artifacts: false     # Whether to capture LLM messages (default: false)
    runs_directory: "runs"                   # Directory for run artifacts (default: runs)               
```

**Parameters:**
- **`name`**: Unique identifier for the pipeline
- **`description`**: Human-readable description of pipeline purpose
- **`agents`**: List of agents to execute in sequence
  - **`name`**: Agent identifier (must match directory in `agents/`)
  - **`input_sources`**: List of where this agent gets input data from:
    - `"pipeline_input"`: Uses the original pipeline input
    - `"agent_name"`: Uses output from specified agent
- **`execution.mode`**: Execution mode (currently only "sequential")
- **`settings`**: Pipeline-level settings
  - **`log_level`**: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) - Default: `INFO`
  - **`create_run_artifacts`**: Whether to create run artifacts - Default: `true`
  - **`include_messages_in_artifacts`**: Whether to capture LLM messages in artifacts - Default: `false`
  - **`runs_directory`**: Directory for storing run artifacts - Default: `runs/`

**Example:**
```yaml
pipeline:
  name: "spec2code_pipeline"
  description: "Generate implementation plans from feature descriptions"
  
  agents:
    - name: "plan_maker"
      input_sources: ["pipeline_input"]
      
    - name: "plan_critique_generator"
      input_sources: ["plan_maker"]
      
    - name: "plan_critique_comparator"
      input_sources: ["pipeline_input", "plan_maker", "plan_critique_generator"]
  
  execution:
    mode: "sequential"
    
  settings:
    log_level: "DEBUG"
    create_run_artifacts: true
    include_messages_in_artifacts: true
    runs_directory: "runs"
```

## Model Configuration (`models/*.yaml`)

Defines LLM model providers, parameters, and credentials. The system uses dynamic provider discovery, supporting any LangChain-compatible provider.

**Generic Structure:**
```yaml
name: "model_identifier"
provider: "provider_name"          # LangChain provider (e.g., "OpenAI")
model_name: "specific_model"       # Provider-specific model name
parameters:                        # Model-specific parameters (passed directly to LLM)
  temperature: 0.7                 # Randomness (0.0-1.0)
  max_tokens: 2000                 # Maximum response tokens
  top_p: 1.0                       # Nucleus sampling (0.0-1.0)
  streaming: false                 # Enable streaming responses
  # Any provider-specific parameters...
credentials:                       # Authentication/connection parameters
  api_key: "${ENV_VAR}"            # Environment variable expansion
  # Any provider-specific credentials...
```

**Parameters:**
- **`name`**: Unique identifier for this model configuration
- **`provider`**: LangChain provider name (e.g., "OpenAI", case is important)
- **`model_name`**: Specific model name within the provider
- **`parameters`**: Dict of model-specific parameters (all parameters are passed directly to the LLM constructor)
- **`credentials`**: Dict of authentication/connection parameters

**Example:**
```yaml
name: "openai_gpt4"
provider: "OpenAI"
model_name: "gpt-4"
parameters:
  temperature: 0.7
  max_tokens: 2000
  top_p: 1.0
  streaming: false
credentials:
  api_key: "${OPENAI_API_KEY}"
```

## Agent Configuration

Agent configuration consists of **two files** that work together:

### Agent Metadata (`agents/*/agent.yaml`)

Defines agent metadata, model reference, and LangChain-specific settings.

**Generic Structure:**
```yaml
name: "agent_name"
description: "Agent purpose description"
llm: "model_config_name"           # Must match filename in models/ directory
```

**Parameters:**
- **`name`**: Agent identifier (should match directory name)
- **`description`**: Human-readable description of agent purpose
- **`llm`**: Reference to model configuration name (must exactly match a file in `models/` directory)

**Example:**  
```yaml
name: "plan_maker"
description: "Creates detailed implementation plans from decomposed steps"
llm: "openai_gpt4"
```

### Prompt Configuration (`agents/*/prompts.yaml`)

Defines prompt templates and system messages for the agent.

**Generic Structure:**
```yaml
system_message: |
  System message defining the agent's role and behavior.
  Can be multi-line.

human_message_template: |
  Template for human messages with variables like {input}.
  This is the fallback when no prompt_templates are defined.

ai_message_prefix: |              # Optional: AI message prefix
  Optional prefix for AI responses.

# prompt_templates supports three valid cases:

# Case 1: Missing/empty (uses only human_message_template)
# prompt_templates: # Omit this field entirely

# Case 2: Single string content (actual template text)
prompt_templates: |
  Custom template content with {input} variables.
  This is actual template text, not a name reference.

# Case 3: Named template variations (dictionary)
prompt_templates:
  template_name1: |
    Template content with {input} variables.
  template_name2: |
    Another template variation.
```

**Parameters:**
- **`system_message`**: (Required) System prompt defining agent's role and behavior
- **`human_message_template`**: (Required) Template for human messages, supports variables like `{input}`
- **`ai_message_prefix`**: (Optional) Prefix for AI responses
- **`prompt_templates`**: (Optional) Three valid formats:
  - **Missing/empty**: Uses only `human_message_template`
  - **Single string**: Actual template content (not a name reference)
  - **Dictionary**: Named template variations for different scenarios

**Template Variables:**
- **`{input}`**: The main input content (if JSON, this is the string representation of the entire JSON object)
- **Any JSON key**: If input is JSON, you can reference any key directly (e.g., `{title}`, `{description}`, `{requirements}`)

**Example:**
```yaml
system_message: |
  You are a technical planning agent. Your role is to create detailed 
  implementation plans from decomposed feature requirements.

human_message_template: |
  Given the following decomposed steps for a feature, create a detailed 
  implementation plan.
  
  Decomposed Steps:
  {input}
  
  Create an implementation plan that includes:
  - Technical approach
  - Implementation steps
  - Dependencies and requirements

prompt_templates:
  with_context: |
    Create an implementation plan including this context: ...
```

#### `prompt_templates` Explanation

The system supports three valid cases for `prompt_templates` configuration:

**Case 1: Missing/Empty Templates**
```yaml
# prompts.yaml - No prompt_templates defined
system_message: |
  You are an agent.
human_message_template: |
  Process this: {input}
```

**Result**: Creates a consolidated execution using only `human_message_template` content since no prompt_templates are defined in `prompts.yaml`.

**Template Execution Flow**:
1. Message chain: `[SystemMessage, HumanMessage(human_message_template)]`
2. Single LLM call processes only the human message template
3. Agent returns consolidated response

```json
// Final output structure
{
  "agents": {
    "agent_name": {
      "output": {
        "agent_response": "Response using human_message_template only",
        "llm_used": true
      },
      "metadata": {
        "execution_time": 123.45,
        "prompt_templates_used": [],  // Empty array - no templates used
        "prompt_templates_count": 0,  // Number of templates processed
        "input_sources": "pipeline_input"
      }
    }
  }
}
```

**Case 2: String Content**
```yaml
# prompts.yaml - String as template content
system_message: |
  You are an agent.
human_message_template: |
  Process this: {input}
prompt_templates: |
  Custom template content with {input} variable.
  This is the actual template text, not a name reference.
```

**Result**: System automatically creates a consolidated execution with both `human_message_template` and the unnamed template content as separate `HumanMessage` objects.

**Template Execution Flow**:
1. Message chain: `[SystemMessage, HumanMessage(human_message_template), HumanMessage(unnamed_content)]`
2. Single LLM call processes both templates together
3. Agent returns consolidated response

```json
// Final output structure
{
  "agents": {
    "agent_name": {
      "output": {
        "agent_response": "Consolidated response using both human_message_template and unnamed content",
        "llm_used": true
      },
      "metadata": {
        "execution_time": 123.45,
        "prompt_templates_used": ["unnamed_template"],  // Internal identifier for unnamed content
        "prompt_templates_count": 1,  // Number of templates processed
        "input_sources": "pipeline_input"
      }
    }
  }
}
```

**Case 3: Named Templates Dictionary**
```yaml
# prompts.yaml - Named templates with content
system_message: |
  You are an agent.
human_message_template: |
  Process this: {input}
prompt_templates:
  with_context: |
    Create a plan for: {input}
    Consider existing context.
  simple_plan: |
    Create a basic plan for: {input}
```

**Result**: All available templates are consolidated into a single agent execution. Each template becomes a separate `HumanMessage` in the LLM conversation.

**Template Execution Flow**:
1. System creates message chain: `[SystemMessage, HumanMessage(human_template), HumanMessage(template1), HumanMessage(template2), ...]`
2. Single LLM call processes all templates together for better context
3. Agent returns consolidated response

```json
// Final output structure
{
  "agents": {
    "agent_name": {
      "output": {
        "agent_response": "Consolidated response considering all templates",
        "llm_used": true
      },
      "metadata": {
        "execution_time": 123.45,
        "prompt_templates_used": ["with_context", "simple_plan"],  // All templates that were processed
        "prompt_templates_count": 2,  // Number of templates processed
        "input_sources": "pipeline_input"
      }
    }
  }
}
```

# Configuration System Guide

This directory contains all configuration files for the spec2code-naive pipeline system. The configuration system supports multi-template execution without requiring code changes.

## Configuration Architecture

The system uses a hierarchical configuration structure:

```
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

## Multi-Input Agent System

Agents specify inputs as a list of sources:

```yaml
agents:
  - name: "plan_maker"
    inputs: ["pipeline_input"]              # Single input from pipeline
  - name: "plan_critique_generator" 
    inputs: ["plan_maker"]                   # Single input from agent
  - name: "plan_critique_comparator"
    inputs: ["plan_maker", "plan_critique_generator"]  # Multi-input from agents
```

### Input Sources
- `"pipeline_input"`: Original input file content
- `"agent_name"`: Output from specified agent
- Multiple sources: Agent receives combined input

### Shared Data Structure

Pipeline maintains unified context:

```json
{
  "pipeline_name": "spec2code_pipeline",
  "execution_successful": true,
  "pipeline_input": {
    "content": "...",
    "source": "input.txt",
    "size": 1322
  },
  "agents": {
    "agent_name": {
      "output": { "agent_response": "..." },
      "metadata": {
        "execution_time": 0.0,
        "templates_used": ["template_name"],
        "input_sources": "pipeline_input"  // or ["agent1", "agent2"]
      }
    }
  },
  "metadata": {
    "agent_sequence": ["agent1", "agent2"],
    "execution_time": 0.0
  }
}
```

### 4. Multi-Template Execution

Agents support multiple prompt templates with flexible configuration:

```yaml
# Single template
prompt_templates: "template_name"

# Multiple templates  
prompt_templates: ["template1", "template2"]

# Auto-all templates (omit field)
# prompt_templates: # Uses all available from prompts.yaml
```

Multi-template output structure:
```json
{
  "template_results": {
    "template1": {...},
    "template2": {...}
  },
  "combined_response": "Aggregated results",
  "execution_metadata": {
    "templates_used": ["template1", "template2"],
    "template_count": 2
  }
}
```

### 5. Log Level Settings

```yaml
settings:
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

## Configuration Types

### 1. Pipeline Configuration (`pipeline.yaml`)

Defines the overall pipeline execution flow, agent sequence, and data mapping.

#### Generic Structure:
```yaml
pipeline:
  name: "pipeline_name"
  description: "Pipeline description"
  
  # Agent execution sequence
  agents:
    - name: "agent_name"              # Must match agent directory name
      input_key: "data_source"        # Where this agent gets its input
      output_key: "result_key"        # Key name for this agent's output
      prompt_templates: "template"    # Optional: specific template(s) to use
  
  # Execution settings
  execution:
    mode: "sequential"               # Currently only sequential supported
    
  # Pipeline-level settings
  settings:
    log_level: "INFO"               # DEBUG, INFO, WARNING, ERROR
    
  # Common model parameters (optional)
  # These parameters are passed to all models, 
  # and can be overridden in individual model configs
  common_model_parameters:
    temperature: 0.7                
    top_p: 1.0                     
    streaming: false               
```

#### Parameters:
- **`name`**: Unique identifier for the pipeline
- **`description`**: Human-readable description of pipeline purpose
- **`agents`**: List of agents to execute in sequence
  - **`name`**: Agent identifier (must match directory in `agents/`)
  - **`input_key`**: Where this agent gets input data from:
    - `"pipeline_input"`: Uses the original pipeline input
    - `"<output_key>"`: Uses output from previous agent with that key
  - **`output_key`**: Key name for storing this agent's output in pipeline data
  - **`prompt_templates`**: (Optional) Which prompt template(s) to use
- **`execution.mode`**: Execution mode (currently only "sequential")
- **`settings.log_level`**: Logging level (DEBUG, INFO, WARNING, ERROR)
- **`common_model_parameters`**: (Optional) Default parameters applied to all models

#### Example:
```yaml
pipeline:
  name: "spec2code_pipeline"
  description: "Generate implementation plans from feature descriptions"
  
  agents:
    - name: "plan_maker"
      input_key: "pipeline_input"
      output_key: "implementation_plan"
      prompt_templates: "with_context"
      
    - name: "plan_critique_generator"
      input_key: "implementation_plan"
      output_key: "critique_report"
      prompt_templates: "technical_feasibility"
      
    - name: "plan_critique_comparator"
      input_key: "critique_report"
      output_key: "comparison_result"
  
  execution:
    mode: "sequential"
    
  settings:
    log_level: "INFO"
    
  common_model_parameters:
    temperature: 0.7
    streaming: false
```

### 2. Model Configuration (`models/*.yaml`)

Defines LLM model providers, parameters, and credentials. The system uses dynamic provider discovery, supporting any LangChain-compatible provider.

#### Generic Structure:
```yaml
name: "model_identifier"
provider: "provider_name"          # LangChain provider (e.g., "openai", "anthropic", "ollama")
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

#### Parameters:
- **`name`**: Unique identifier for this model configuration
- **`provider`**: LangChain provider name (used for dynamic import: `langchain_{provider}`)
- **`model_name`**: Specific model name within the provider
- **`parameters`**: Dict of model-specific parameters (all parameters are passed directly to the LLM constructor)
- **`credentials`**: Dict of authentication/connection parameters

#### Example:
```yaml
name: "openai_gpt4"
provider: "openai"
model_name: "gpt-4"
parameters:
  temperature: 0.7
  max_tokens: 2000
  top_p: 1.0
  streaming: false
credentials:
  api_key: "${OPENAI_API_KEY}"
```

### 3. Agent Configuration

Agent configuration consists of **two files** that work together:

#### 3.1. Agent Metadata (`agents/*/agent.yaml`)

Defines agent metadata, model reference, and LangChain-specific settings.

##### Generic Structure:
```yaml
name: "agent_name"
description: "Agent purpose description"
llm: "model_config_name"           # Must match filename in models/ directory
tools:                             # Optional: Tool configurations
  - name: "tool_name"
    description: "Tool description"
    _type: "tool_type"
    # Tool-specific parameters...
memory:                            # Optional: Memory configuration
  _type: "memory_type"
  max_token_limit: 2000
agent_type: "agent_type"           # Optional: LangChain agent type
max_iterations: 3                  # Optional: Maximum execution iterations
early_stopping_method: "generate"  # Optional: Stopping method
```

##### Parameters:
- **`name`**: Agent identifier (should match directory name)
- **`description`**: Human-readable description of agent purpose
- **`llm`**: Reference to model configuration name (must exactly match a file in `models/` directory)
- **`tools`**: (Optional) List of tool configurations for the agent
- **`memory`**: (Optional) Memory configuration for the agent
- **`agent_type`**: (Optional) LangChain agent type (default: "zero-shot-react-description")
- **`max_iterations`**: (Optional) Maximum execution iterations (default: 3)
- **`early_stopping_method`**: (Optional) Early stopping method (default: "generate")

##### Example:
```yaml
name: "plan_maker"
description: "Creates detailed implementation plans from decomposed steps"
llm: "openai_gpt4"
tools:
  - name: "file_reader"
    description: "Read context files for planning"
    _type: "file_reader"
    base_path: "./context"
memory:
  _type: "buffer"
  max_token_limit: 2000
```

#### 3.2. Prompt Configuration (`agents/*/prompts.yaml`)

Defines prompt templates and system messages for the agent.

##### Generic Structure:
```yaml
system_message: |
  System message defining the agent's role and behavior.
  Can be multi-line.

human_message_template: |
  Template for human messages with variables like {input}.
  This is the fallback when no prompt_templates are defined.

ai_message_prefix: |              # Optional: AI message prefix
  Optional prefix for AI responses.

prompt_templates:                 # Optional: Named template variations
  template_name1: |
    Template content with {input} variables.
  template_name2: |
    Another template variation.
```

##### Parameters:
- **`system_message`**: (Required) System prompt defining agent's role and behavior
- **`human_message_template`**: (Required) Template for human messages, supports variables like `{input}`
- **`ai_message_prefix`**: (Optional) Prefix for AI responses
- **`prompt_templates`**: (Optional) Dict of named template variations for different scenarios

##### Template Variables:
- **`{input}`**: The main input content
- **`{decomposed_steps}`**: Alias for input (legacy compatibility)
- **Any key from input JSON**: Can reference specific input fields

##### Example:
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
    Create an implementation plan for: {input}
    
    Consider the existing codebase context and dependencies.
  
  simple_plan: |
    Create a basic implementation plan for: {input}
```
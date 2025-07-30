# Configuration System Guide

This directory contains all configuration files for the spec2code-naive pipeline system. The configuration system supports multi-template execution, always-on validation, and configurable logging without requiring code changes.

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

## Input-Output Data Flow Mechanism

The pipeline maintains a **shared data context** that gets built up as each agent executes. Here's exactly how the data flows through the system:

### 1. Initial Pipeline Data Structure
When the pipeline starts, it creates a data context:
```json
{
  "pipeline_input": "Original input text from file",
  "agent_outputs": {},
  "execution_metadata": {...}
}
```

### 2. Agent Execution and Data Mapping

Each agent in the pipeline config specifies:
- **`input_key`**: Where to get input data FROM
- **`output_key`**: Where to store output data TO

Let's trace through the actual execution:

#### Agent 1: plan_maker
```yaml
- name: "plan_maker"
  input_key: "pipeline_input"      # Gets original input
  output_key: "implementation_plan"    # Stores result here
```

**Execution:**
1. Agent gets input: `pipeline_data["pipeline_input"]` 
2. Agent processes and returns: `{"output": {...}, "metadata": {...}}`
3. System stores:
   - `pipeline_data["agent_outputs"]["plan_maker"] = full_agent_response`
   - `pipeline_data["implementation_plan"] = agent_response["output"]`

**Pipeline data after Agent 1:**
```json
{
  "pipeline_input": "Original input text",
  "implementation_plan": {
    "agent_response": "Generated implementation plan...",
    "processed_input": {...},
    "agent_type": "plan_maker"
  },
  "agent_outputs": {
    "plan_maker": {"output": {...}, "metadata": {...}}
  }
}
```

#### Agent 2: plan_critique_generator
```yaml
- name: "plan_critique_generator"
  input_key: "implementation_plan"  # Gets previous agent's output
  output_key: "critique_report"         # Stores result here
```

**Execution:**
1. Agent gets input: `pipeline_data["implementation_plan"]` (from Agent 1)
2. Agent processes and returns: `{"output": {...}, "metadata": {...}}`
3. System stores:
   - `pipeline_data["agent_outputs"]["plan_critique_generator"] = full_agent_response`
   - `pipeline_data["critique_report"] = agent_response["output"]`

### 3. Key Input Key Options

- **`"pipeline_input"`**: Uses the original input text from the file
- **`"<any_output_key>"`**: Uses the output from whichever agent wrote to that key
- **Future**: Could support complex mappings like `"agent_outputs.plan_maker.metadata"`

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

### 5. Pipeline Settings

```yaml
settings:
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

- **Dry Run**: Always available via `--dry-run` flag
- **Logging**: Always enabled, level configurable
- **Validation**: Always enforced at runtime

### 6. The Critical Insight

The `output_key` creates a **named slot** in the pipeline data that subsequent agents can reference via `input_key`. This creates a **declarative data flow** where:

- You define WHAT data flows WHERE
- You don't need to hardcode HOW agents connect
- You can easily reorder, add, or remove agents
- Each agent's output becomes available to all subsequent agents

This is why the system is so flexible - the pipeline configuration acts as a **data flow graph** that you can modify without touching any code.

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
  common_model_parameters:
    temperature: 0.7                # Applied to all models unless overridden
    top_p: 1.0                     # Applied to all models unless overridden
    streaming: false               # Applied to all models unless overridden
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
  top_p: 1.0                      # Nucleus sampling (0.0-1.0)
  streaming: false                 # Enable streaming responses
  # Any provider-specific parameters...
credentials:                       # Authentication/connection parameters
  api_key: "${ENV_VAR}"           # Environment variable expansion
  # Any provider-specific credentials...
```

#### Parameters:
- **`name`**: Unique identifier for this model configuration
- **`provider`**: LangChain provider name (used for dynamic import: `langchain_{provider}`)
- **`model_name`**: Specific model name within the provider
- **`parameters`**: Dict of model-specific parameters - **all parameters are passed directly to the LLM constructor**
- **`credentials`**: Dict of authentication/connection parameters

#### Parameter Pass-Through System:
The system passes **all parameters** from the model config directly to the LLM constructor. This means:
- Provider-specific parameters work automatically (e.g., `num_predict` for Ollama)
- No parameter mapping needed
- You can add any provider-specific parameter to your model config
- Common parameters from pipeline config are merged with individual model parameters
- Individual model parameters take precedence over common parameters

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

## Environment Variables

The system supports secure credential management through environment variable expansion:

```yaml
credentials:
  api_key: "${OPENAI_API_KEY}"      # Expands to value of OPENAI_API_KEY
  custom_param: "${CUSTOM_VAR}"     # Expands to value of CUSTOM_VAR
```

### Required Environment Variables:
- **OpenAI**: `OPENAI_API_KEY`
- **Anthropic**: `ANTHROPIC_API_KEY`
- **Ollama**: Usually none (runs locally)

## Adding New Providers

The system uses dynamic provider discovery, making it easy to add new LangChain providers:

1. **Install the provider package**:
   ```bash
   pip install langchain-{provider}
   ```

2. **Create model configuration**:
   ```yaml
   # config/models/new_provider_model.yaml
   name: "new_provider_model"
   provider: "new_provider"  # Must match package name
   model_name: "specific_model"
   parameters:
     # Provider-specific parameters
   credentials:
     # Provider-specific credentials
   ```

3. **Reference in agent config**:
   ```yaml
   # config/agents/*/agent.yaml
   llm: "new_provider_model"
   ```

The system automatically discovers the provider using the naming convention:
- **Package**: `langchain_{provider}`
- **Class**: `Chat{Provider}` (title case)

## Adding New Agents

To add a new agent to the pipeline:

1. **Create agent directory**:
   ```bash
   mkdir config/agents/new_agent
   ```

2. **Create agent configuration**:
   ```yaml
   # config/agents/new_agent/agent.yaml
   name: "new_agent"
   description: "Description of what this agent does"
   llm: "openai_gpt4"  # Reference to model config
   ```

3. **Create prompt templates**:
   ```yaml
   # config/agents/new_agent/prompts.yaml
   system_message: |
     You are a specialized agent that...
   
   human_message_template: |
     Process this input: {input}
   ```

4. **Add to pipeline**:
   ```yaml
   # config/pipeline.yaml
   agents:
     # ... existing agents
     - name: "new_agent"
       input_key: "previous_output_key"
       output_key: "new_agent_output"
   ```

## Configuration Validation

The system includes comprehensive configuration validation:

- **YAML syntax validation**
- **Required field checking**
- **Reference validation** (model references, agent names)
- **Parameter type checking**
- **Environment variable validation**

Use the CLI tool for validation:
```bash
python cli_config.py validate
```

## Best Practices

### Model Configuration:
- Use descriptive names for model configs
- Set reasonable token limits to control costs
- Use environment variables for all credentials
- Test with different temperature settings for your use case
- All parameters are passed directly to the LLM - add any provider-specific parameters

### Agent Configuration:
- Keep agent names short and descriptive
- Use clear descriptions for documentation
- Choose appropriate models for each agent's complexity
- The `llm` field must exactly match the model config filename

### Prompt Configuration:
- Write clear, specific system messages
- Use template variables for flexibility
- Test prompts with different input types
- `prompt_templates` are optional - the system falls back to `human_message_template`

### Pipeline Configuration:
- Design clear data flow between agents
- Use descriptive output keys
- Consider the order of agent execution carefully
- Test with dry-run mode before using real LLMs
- Use common model parameters for consistent behavior across agents

## Troubleshooting

### Common Configuration Issues:

1. **Invalid YAML syntax**: Use a YAML validator or linter
2. **Missing model references**: Ensure model names match file names exactly
3. **Environment variables not set**: Check required variables for your provider
4. **Provider not found**: Install the correct `langchain-{provider}` package
5. **Template variable errors**: Ensure all `{variables}` are provided in input

### Debugging Tips:
- Use `--dry-run` mode to test configuration without LLM calls
- Check logs for detailed error messages
- Validate configurations with `python cli_config.py validate`
- Test individual components before full pipeline runs

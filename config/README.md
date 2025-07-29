# Configuration System Guide

This directory contains all configuration files for the spec2code-naive pipeline system. The configuration system is designed to be fully declarative, allowing you to modify system behavior without touching any code.

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
- **`input_mapping`**: Where to get input data FROM
- **`output_key`**: Where to store output data TO

Let's trace through the actual execution:

#### Agent 1: plan_maker
```yaml
- name: "plan_maker"
  input_mapping: "pipeline_input"      # Gets original input
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
  input_mapping: "implementation_plan"  # Gets previous agent's output
  output_key: "critique_report"         # Stores result here
```

**Execution:**
1. Agent gets input: `pipeline_data["implementation_plan"]` (from Agent 1)
2. Agent processes and returns: `{"output": {...}, "metadata": {...}}`
3. System stores:
   - `pipeline_data["agent_outputs"]["plan_critique_generator"] = full_agent_response`
   - `pipeline_data["critique_report"] = agent_response["output"]`

**Pipeline data after Agent 2:**
```json
{
  "pipeline_input": "Original input text",
  "implementation_plan": {...},
  "critique_report": {
    "agent_response": "Generated critique report...",
    "processed_input": {...},
    "agent_type": "plan_critique_generator"
  },
  "agent_outputs": {
    "plan_maker": {...},
    "plan_critique_generator": {...}
  }
}
```

#### Agent 3: plan_critique_comparator
```yaml
- name: "plan_critique_comparator"
  input_mapping: "critique_report"     # Gets Agent 2's output
  output_key: "comparison_result"      # Stores result here
```

**Execution:**
1. Agent gets input: `pipeline_data["critique_report"]` (from Agent 2)
2. Agent processes and returns final result
3. System stores both detailed and final outputs

### 3. Key Input Mapping Options

- **`"pipeline_input"`**: Uses the original input text from the file
- **`"<any_output_key>"`**: Uses the output from whichever agent wrote to that key
- **Future**: Could support complex mappings like `"agent_outputs.plan_maker.metadata"`

### 4. Data Structure at Each Agent

When an agent receives input, it gets a JSON structure like:
```json
{
  "input": <the_mapped_data>
}
```

When an agent returns output, it provides:
```json
{
  "output": {
    "agent_response": "LLM generated text",
    "processed_input": <original_input>,
    "agent_type": "agent_name"
  },
  "metadata": {
    "agent_name": "agent_name",
    "dry_run": false,
    "input_received": true
  }
}
```

### 5. The Critical Insight

The `output_key` creates a **named slot** in the pipeline data that subsequent agents can reference via `input_mapping`. This creates a **declarative data flow** where:

- You define WHAT data flows WHERE
- You don't need to hardcode HOW agents connect
- You can easily reorder, add, or remove agents
- Each agent's output becomes available to all subsequent agents

This is why the system is so flexible - the pipeline configuration acts as a **data flow graph** that you can modify without touching any code.

## Configuration Types

### 1. Pipeline Configuration (`pipeline.yaml`)

Defines the overall pipeline execution flow, agent sequence, and data mapping.

```yaml
name: "spec2code_pipeline"
execution_mode: "sequential"  # Currently only sequential supported
agents:
  - name: "plan_maker"                    # Must match agent directory name
    input_mapping: "pipeline_input"      # Where this agent gets its input
    output_key: "implementation_plan"    # Key name for this agent's output
    prompt_template: "default"           # Which prompt template to use
  - name: "plan_critique_generator"
    input_mapping: "implementation_plan" # Uses previous agent's output
    output_key: "critique_report"
    prompt_template: "technical_feasibility"
  - name: "plan_critique_comparator"
    input_mapping: "critique_report"
    output_key: "comparison_result"
    prompt_template: "default"
```

#### Pipeline Parameters:
- **`name`**: Pipeline identifier (string)
- **`execution_mode`**: How agents are executed (`"sequential"` only for now)
- **`agents`**: List of agent execution configurations

#### Agent Execution Parameters:
- **`name`**: Agent name (must match directory in `agents/`)
- **`input_mapping`**: Where this agent gets input data from:
  - `"pipeline_input"`: Uses the original pipeline input
  - `"<output_key>"`: Uses output from previous agent with that key
- **`output_key`**: Key name for storing this agent's output in pipeline data
- **`prompt_template`**: Which prompt template to use (`"default"` or specific template name)

### 2. Model Configuration (`models/*.yaml`)

Defines LLM model providers, parameters, and credentials. The system uses dynamic provider discovery, supporting any LangChain-compatible provider.

#### Generic Model Structure:
```yaml
name: "model_identifier"
provider: "provider_name"     # e.g., "openai", "anthropic", "ollama"
model_name: "specific_model"  # e.g., "gpt-4", "claude-3-sonnet"
parameters:                   # Provider-specific parameters
  temperature: 0.7
  max_tokens: 2000
  # ... any other parameters
credentials:                  # Provider-specific credentials
  api_key: "${API_KEY_VAR}"   # Environment variable expansion
  # ... any other credentials
```

#### OpenAI Example (`models/openai_gpt4.yaml`):
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

#### Anthropic Example (`models/anthropic_claude.yaml`):
```yaml
name: "anthropic_claude"
provider: "anthropic"
model_name: "claude-3-sonnet-20240229"
parameters:
  temperature: 0.7
  max_tokens: 2000
credentials:
  api_key: "${ANTHROPIC_API_KEY}"
```

#### Ollama Example (`models/ollama_llama.yaml`):
```yaml
name: "ollama_llama"
provider: "ollama"
model_name: "llama2"
parameters:
  temperature: 0.7
  num_predict: 2000
credentials:
  base_url: "http://localhost:11434"
```

#### Model Configuration Parameters:
- **`name`**: Unique identifier for this model configuration
- **`provider`**: LangChain provider name (used for dynamic import: `langchain_{provider}`)
- **`model_name`**: Specific model name within the provider
- **`parameters`**: Dict of model-specific parameters (temperature, max_tokens, etc.)
- **`credentials`**: Dict of authentication/connection parameters

#### Common Model Parameters:
- **`temperature`**: Randomness in output (0.0-1.0, default: 0.7)
- **`max_tokens`**: Maximum tokens in response (default: 2000)
- **`top_p`**: Nucleus sampling parameter (0.0-1.0, default: 1.0)
- **`streaming`**: Enable streaming responses (boolean, default: false)

### 3. Agent Configuration (`agents/*/agent.yaml`)

Defines agent metadata and model references.

```yaml
name: "plan_maker"
description: "Creates detailed implementation plans from feature descriptions"
llm: "openai_gpt4"  # References a model config by name
```

#### Agent Parameters:
- **`name`**: Agent identifier (should match directory name)
- **`description`**: Human-readable description of agent purpose
- **`llm`**: Reference to model configuration name (from `models/` directory)

### 4. Prompt Configuration (`agents/*/prompts.yaml`)

Defines prompt templates and system messages for each agent.

```yaml
system_message: |
  You are a technical planning agent. Your role is to create detailed 
  implementation plans from decomposed feature requirements.

human_message_template: |
  Given the following decomposed steps for a feature, create a detailed 
  implementation plan.
  
  Decomposed Steps:
  {decomposed_steps}
  
  Create an implementation plan that includes:
  1. Ordered sequence of implementation tasks
  2. Dependencies between tasks  
  3. Estimated complexity for each task
  4. Required resources/technologies

# Optional: Multiple prompt templates
templates:
  technical_feasibility: |
    Analyze the technical feasibility of the following implementation plan:
    {input}
    
    Focus on:
    - Technical complexity assessment
    - Resource requirements
    - Potential risks and challenges
  
  default: |
    Process the following input:
    {input}
```

#### Prompt Parameters:
- **`system_message`**: System message sent to the LLM (sets agent behavior/role)
- **`human_message_template`**: Template for human messages with variable substitution
- **`templates`**: Optional dict of named prompt templates for different use cases

#### Template Variables:
Templates support variable substitution using `{variable_name}` syntax:
- **`{input}`**: The main input content
- **`{decomposed_steps}`**: Alias for input (legacy compatibility)
- **Any key from input JSON**: Can reference specific input fields

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
       input_mapping: "previous_output_key"
       output_key: "new_agent_output"
       prompt_template: "default"
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

### Agent Configuration:
- Keep agent names short and descriptive
- Use clear descriptions for documentation
- Choose appropriate models for each agent's complexity

### Prompt Configuration:
- Write clear, specific system messages
- Use template variables for flexibility
- Test prompts with different input types
- Consider creating multiple templates for different scenarios

### Pipeline Configuration:
- Design clear data flow between agents
- Use descriptive output keys
- Consider the order of agent execution carefully
- Test with dry-run mode before using real LLMs

## Troubleshooting

### Common Configuration Issues:

1. **Invalid YAML syntax**: Use a YAML validator or linter
2. **Missing model references**: Ensure model names match file names
3. **Environment variables not set**: Check required variables for your provider
4. **Provider not found**: Install the correct `langchain-{provider}` package
5. **Template variable errors**: Ensure all `{variables}` are provided in input

### Debugging Tips:
- Use `--dry-run` mode to test configuration without LLM calls
- Check logs for detailed error messages
- Validate configurations with `python cli_config.py validate`
- Test individual components before full pipeline runs

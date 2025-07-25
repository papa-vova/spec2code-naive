# spec2code-naïve

## Project Overview
A multi-agent LangChain application that generates implementation plans from feature descriptions. The system processes free-text descriptions through a pipeline of planning, critique generation, and metric comparison.

## Directory Structure

```
spec2code-naive/
├── main.py                           # Main entry point and pipeline orchestration
├── requirements.txt                  # Python dependencies
├── sample_input_description.txt      # Sample input file for testing
├── cli_config.py                    # CLI configuration management tool
│
├── agents/                          # Core agent implementations
│   ├── __init__.py                  # Package initialization
│   ├── plan_maker.py               # Agent that creates implementation plans
│   ├── plan_critique_generator.py  # Agents that generate critical reports
│   └── plan_critique_comparator.py # Agent that compares reports and generates metrics
│
├── config/                          # Configuration files for agents and models
│   ├── models/
│   │   └── openai_gpt4.yaml        # OpenAI GPT-4 model configuration
│   └── agents/
│       ├── plan_maker/
│       │   ├── agent.yaml          # Plan maker agent configuration
│       │   └── prompts.yaml        # Plan maker prompts and templates
│       ├── plan_critique_generator/
│       │   ├── agent.yaml          # Critique generator agent configuration
│       │   └── prompts.yaml        # Critique generator prompts and templates
│       └── plan_critique_comparator/
│           ├── agent.yaml          # Comparator agent configuration
│           └── prompts.yaml        # Comparator prompts and templates
│
├── config_system/                  # Configuration loading and validation system
│   ├── __init__.py                 # Package initialization
│   └── config_loader.py           # Configuration loader with validation
│
└── docs/                           # Documentation and specifications
    ├── spec2code-naïve raw initial plan.md    # Original project plan
    ├── spec2code - a bit less naïve flow.pdf  # Flow diagram (PDF)
    └── spec2code - a bit less naïve flow.jpg  # Flow diagram (Image)
```

## File Descriptions

### Core Application Files

**`main.py`**
- Main entry point for the application
- Implements the `Pipeline` class that orchestrates the entire workflow
- Handles CLI argument parsing (requires `-i/--input` for input file)
- Executes steps: plan creation → report generation → metric comparison
- Provides comprehensive error handling and user feedback

**`requirements.txt`**
- Lists Python package dependencies
- Includes LangChain, OpenAI, and other required libraries

**`sample_input_description.txt`**
- Sample input file containing a feature description
- Used for testing the pipeline with a task management application example
- Can be replaced with any project description

**`cli_config.py`**
- CLI configuration utilities
- Handles command-line argument processing and validation

### Agent Implementations

**`agents/plan_maker.py`**
- `PlanMakerAgent`: Creates detailed implementation plans from feature descriptions
- Takes free-text input and generates structured implementation tasks
- Uses LangChain prompts and can integrate with LLM models
- Includes fallback skeleton implementation for testing

**`agents/plan_critique_generator.py`**
- `ReportGeneratorAgent`: Generates critical analysis reports on implementation plans
- Creates multiple independent reports with different focus areas:
  - Technical feasibility analysis
  - Resource adequacy assessment
  - Timeline realism evaluation
  - Dependency analysis
- Each report includes scores, summaries, and detailed feedback

**`agents/plan_critique_comparator.py`**
- `MetricComparatorAgent`: Compares multiple reports and generates final metrics
- Analyzes consistency across different critique reports
- Generates aggregate scores and recommendations
- Determines if the plan is acceptable or needs revision

### Configuration System

**`config_system/config_loader.py`**
- `ConfigLoader`: Loads and validates YAML configuration files
- Handles model configurations (temperature, tokens, etc.)
- Manages agent configurations (tools, memory, prompts)
- Provides caching and validation for all config files
- Supports LangChain message types and prompt templates

**`config/models/openai_gpt4.yaml`**
- Configuration for OpenAI GPT-4 model
- Defines model parameters: temperature, max_tokens, top_p
- Includes API key reference and streaming settings

**`config/agents/*/agent.yaml`**
- Agent-specific configurations
- Defines LLM model to use, tools, memory settings
- Specifies agent type and execution parameters

**`config/agents/*/prompts.yaml`**
- Prompt templates for each agent
- System messages, human message templates
- Specialized prompts for different report types

### Documentation

**`docs/spec2code-naïve raw initial plan.md`**
- Original project specification and planning document
- Describes the multi-agent workflow and implementation approach
- Contains detailed flow descriptions for planning/analysis branch

**`docs/spec2code - a bit less naïve flow.*`**
- Visual flow diagrams showing the complete pipeline process
- Available in both PDF and JPG formats
- Illustrates decision points and data flow between agents

## Usage

### Main Pipeline

```bash
# Run the pipeline with an input file
python main.py -i input_description.txt

# Show help
python main.py --help

# Example with custom input file
python main.py -i my_project_description.txt
```

### Configuration Management CLI

The `cli_config.py` tool provides configuration management commands:

#### Available Commands

**VALIDATE** - Validate all configuration files
```bash
python cli_config.py validate
```
- Validates all YAML configuration files for syntax and structure
- Checks models, agents, and prompts for correctness
- Returns success/failure with detailed error messages

**LIST** - List available models and agents
```bash
python cli_config.py list
```
- Shows all available models from `config/models/`
- Shows all available agents from `config/agents/`
- Useful for seeing what's configured in your system

**CHECK** - Check specific configuration
```bash
# Check a specific model
python cli_config.py check --model openai_gpt4

# Check a specific agent
python cli_config.py check --agent plan_maker

# Check both model and agent
python cli_config.py check --model openai_gpt4 --agent plan_maker
```
- Validates and displays details for specific model or agent
- Shows configuration parameters, tools, prompt templates
- Helpful for debugging specific agent issues

#### Global Options

```bash
# Use custom config directory
python cli_config.py --config-root ./my-configs validate

# Show detailed help
python cli_config.py --help
python cli_config.py
```

#### Example Workflow

```bash
# 1. Validate all configurations before deployment
python cli_config.py validate

# 2. List available resources
python cli_config.py list

# 3. Check specific configurations during development
python cli_config.py check --agent plan_maker

# 4. Use with custom config directory
python cli_config.py --config-root ./test-configs validate
```

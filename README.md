# spec2code-naïve

## Project Overview
A fully configurable, multi-agent LangChain pipeline system that processes feature descriptions through sequential agent execution. The system features a unified agent architecture with dynamic model provider discovery, enabling zero-maintenance support for any LangChain-compatible LLM provider.

## Key Features
- **Unified Agent Architecture**: Single `Agent` class configured entirely through YAML files
- **Dynamic Model Provider Discovery**: Automatic support for any LangChain provider (OpenAI, Anthropic, Ollama, etc.)
- **Config-Driven Pipeline**: Sequential agent execution defined by `pipeline.yaml`
- **JSON I/O Pipeline**: Standardized data passing between agents
- **Comprehensive Logging**: Structured JSON logging throughout execution
- **Zero Hardcoded Logic**: Everything configurable via YAML files

## Directory Structure

```
spec2code-naive/
├── main.py                           # Main entry point and CLI interface
├── requirements.txt                  # Python dependencies
├── sample_input.txt                  # Sample input file for testing
├── cli_config.py                     # CLI configuration management tool
├── exceptions.py                     # Custom exception classes for error handling
├── logging_config.py                 # JSON logging configuration and utilities
│
├── core/                             # Core system components
│   ├── agent.py                      # Unified Agent class with LangChain execution
│   └── orchestrator.py               # Config-driven pipeline orchestrator
│
├── config/                           # Configuration files for agents, models, and pipeline
│   ├── pipeline.yaml                 # Pipeline configuration (agent sequence, I/O mapping)
│   ├── models/
│   │   ├── openai_gpt4.yaml          # OpenAI GPT-4 model configuration
│   │   ├── anthropic_claude.yaml     # Anthropic Claude model configuration
│   │   └── ollama_llama.yaml         # Ollama Llama model configuration
│   └── agents/
│       ├── plan_maker/
│       │   ├── agent.yaml            # Plan maker agent configuration
│       │   └── prompts.yaml          # Plan maker prompts and templates
│       ├── plan_critique_generator/
│       │   ├── agent.yaml            # Critique generator agent configuration
│       │   └── prompts.yaml          # Critique generator prompts and templates
│       └── plan_critique_comparator/
│           ├── agent.yaml            # Comparator agent configuration
│           └── prompts.yaml          # Comparator prompts and templates
│
├── config_system/                    # Configuration loading and validation system
│   ├── __init__.py                   # Package initialization
│   ├── config_loader.py              # Configuration loader with validation
│   └── agent_factory.py              # Dynamic agent and model factory
│
└── docs/                             # Documentation and specifications
    ├── spec2code-naïve raw initial plan.md    # Original project plan
    ├── spec2code - a bit less naïve flow.pdf  # Flow diagram (PDF)
    └── spec2code - a bit less naïve flow.jpg  # Flow diagram (Image)
```

## Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd spec2code-naive

# Install dependencies
pip install -r requirements.txt

# Install your preferred LangChain provider (examples):
pip install langchain-openai      # For OpenAI models
pip install langchain-anthropic   # For Anthropic models  
pip install langchain-ollama      # For Ollama models
# Any Future Provider:
# Just install the langchain-{provider} package and set provider name in config
```

### Environment Setup
```bash
# Set your API key (choose one based on your provider)
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
# Ollama runs locally, no API key needed
```

### Usage
```bash
# Run with dry-run mode (no LLM calls, uses dummy outputs)
python main.py -i sample_input.txt --dry-run

# Run with actual LLM execution
python main.py -i sample_input.txt

# Use custom config directory
python main.py -i sample_input.txt --config-root /path/to/config
```

## Architecture Overview

### Core Components

**`core/agent.py`** - Unified Agent Class
- Single `Agent` class that replaces all individual agent implementations
- Configured entirely through YAML files (no hardcoded logic)
- Supports actual LangChain execution with any provider
- Handles prompt templates, system messages, and JSON I/O
- Includes comprehensive error handling and logging

**`core/orchestrator.py`** - Pipeline Orchestrator
- Config-driven orchestrator that executes agents sequentially
- Loads pipeline configuration from `config/pipeline.yaml`
- Manages JSON data passing between agents
- Provides detailed logging and error handling
- Supports different execution modes (sequential, future: parallel)

**`config_system/`** - Configuration System
- **`config_loader.py`**: Loads and validates all YAML configurations
- **`agent_factory.py`**: Dynamic factory with zero-maintenance model provider discovery
- Supports any LangChain provider through naming conventions
- Automatic credential and parameter handling

## System Features

### Dynamic Model Provider Discovery
- **Zero Maintenance**: Automatically supports any LangChain provider without code changes
- **Naming Convention**: Uses `langchain_{provider}` + `Chat{Provider}` pattern
- **Generic Parameters**: Any provider-specific parameters supported through config
- **Environment Variables**: Secure credential management with `${VAR_NAME}` expansion

### Pipeline Execution Flow
1. **Input Processing**: Reads feature description from file
2. **Agent Orchestration**: Executes agents sequentially based on pipeline config
3. **Data Passing**: JSON output from each agent becomes input for the next
4. **Logging**: Comprehensive structured logging throughout execution
5. **Error Handling**: Graceful failure with detailed error messages

## Usage

### Main Pipeline

```bash
# Run the pipeline with an input file:
python main.py -i sample_input.txt

# With logging options
python main.py -i sample_input.txt --log-level DEBUG
python main.py -i sample_input.txt --verbose

# With custom configuration directory
python main.py -i sample_input.txt --config-root ./my-configs

# Show help for all options
python main.py --help
```

### Configuration Management

Use the configuration management CLI for setup and validation:
```bash
# Validate all configurations
python cli_config.py validate

# List available models and agents  
python cli_config.py list

# Check specific configurations
python cli_config.py check --agent plan_maker

# With custom configuration directory
python cli_config.py --config-root ./my-configs validate

# Show detailed help
python cli_config.py --help
```

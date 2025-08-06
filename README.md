# spec2code-naïve

Multi-agent LangChain pipeline that processes input through sequential agent execution. Agents are configured via YAML files and can use any LangChain-compatible LLM provider.

## How It Works

- Agents execute sequentially as defined in the [configuration](config/README.md)
- Each agent can take input from pipeline input or other agents
- Multi-input agents supported (agent can read from multiple sources)
- All configuration via YAML files, no code changes needed
- Logs go to `stderr` (JSON format), structured output to `stdout`
- Exit codes: 0 = success, 1 = failure

## Structure

```bash
spec2code-naive/
├── main.py                    # CLI entry point
├── test_runtime.py            # Regression tests
├── test_config.py             # Config validation tool
├── requirements.txt           # Python dependencies
├── sample_input.txt           # Example input file
├── logging_config.py          # Logging configuration
├── exceptions.py              # Custom exceptions
├── core/
│   ├── agent.py               # Agent execution
│   ├── orchestrator.py        # Pipeline orchestration
│   └── run_manager.py         # Run storage and metadata
├── config/
│   ├── README.md                  # Configuration system documentation
│   ├── pipeline.yaml              # Agent sequence and inputs
│   ├── models/                    # LLM provider configs
│   │   ├── openai_gpt4.yaml       # OpenAI configuration
│   │   ├── anthropic_claude.yaml  # Anthropic configuration
│   │   └── ollama_llama.yaml      # Ollama configuration
│   └── agents/                    # Agent configs and prompts
│       ├── plan_maker/
│       │   ├── agent.yaml         # Agent metadata
│       │   └── prompts.yaml       # Prompt templates
│       ├── plan_critique_generator/
│       │   ├── agent.yaml         # Agent metadata
│       │   └── prompts.yaml       # Prompt templates
│       └── plan_critique_comparator/
│           ├── agent.yaml         # Agent metadata
│           └── prompts.yaml       # Prompt templates
├── config_system/
│   ├── __init__.py              # Package initialization
│   ├── config_loader.py         # Config loading and validation
│   └── agent_factory.py         # Agent instantiation
├── runs/                        # Run output storage
│   ├── 20250801_151701_1884a7b5/     # Results of the run
│   │   ├── result.json               # Pipeline output
│   │   └── metadata.json             # Run metadata
│   └── ...
└── docs/                      # Documentation
    ├── spec2code-naïve raw initial plan.md
    ├── spec2code - a bit less naïve flow.pdf
    └── spec2code - a bit less naïve flow.jpg
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt
pip install langchain-openai  # or your preferred provider

# Set API key
export OPENAI_API_KEY="your-key" # or your preferred provider's key

# Run pipeline
python main.py -i sample_input.txt
# python main.py --help for more options

# Test configuration
python test_config.py validate
# python test_config.py --help for more options

# Run regression tests
python test_runtime.py

# CI/CD pipeline
python test_config.py validate && python test_runtime.py && python main.py -i input.txt
```

## Configuration

See [config/README.md](config/README.md) for configuration details.

## Run System & Output Artifacts

### Run System

Execution flow:
1. Input content is loaded from specified file(s)
2. Configuration is validated from YAML files
3. Agents execute sequentially as defined in `pipeline.yaml`
4. Each agent processes inputs according to its configuration
5. Results are structured into a unified JSON output
6. Structured output is sent to `stdout`, logs to `stderr`
7. Output artifacts are stored in run-specific directory

### Run Folders Structure

Each pipeline execution creates a dedicated run folder with unique ID:

```bash
runs/
├── 20250801_174513_12345678/    # Format: timestamp_uuid
│   ├── result.json              # Complete execution output
│   └── metadata.json            # Run metadata
└── 20250801_180042_87654321/
    ├── result.json
    └── metadata.json
```

#### Metadata File

Each run generates a `metadata.json` file containing:

```json
{
  "run_id": "20250801_174513_12345678",
  "timestamp": "2025-08-01T17:45:13.123456",  // Recorded at completion time
  "config_root": "/absolute/path/to/config",
  "input_file": "/absolute/path/to/sample_input.txt",
  "pipeline_name": "spec2code_pipeline",
  "execution_successful": true,
  "agent_count": 3,
  "total_execution_time": 10.5
}
```

This provides a complete record of the run context, including input file and execution statistics.

### Output Artifacts

The pipeline produces a structured JSON output with the following components:

```json
{
  "pipeline_name": "spec2code_pipeline",
  "execution_successful": true,
  "pipeline_input": {
    "content": "...",  // Original input content!
    "source": "input.txt",
    "size": 1322
  },
  "agents": {
    "agent_name": {
      "output": { 
        "agent_response": "..."
      },
      "messages": [  // Optional: only when include_messages_in_artifacts: true
        {
          "type": "system",
          "content": "You are a business analyst..."
        },
        {
          "type": "human", 
          "content": "Please analyze the following requirements..."
        },
        {
          "type": "ai",
          "content": "I'll help you analyze..."
        }
      ],
      "metadata": {
        "execution_time": 0.0,
        "prompt_templates_used": ["template_name"],
        "prompt_templates_count": 1,
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

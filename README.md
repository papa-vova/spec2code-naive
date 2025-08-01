# spec2code-naïve

Multi-agent LangChain pipeline that processes input through sequential agent execution. Agents are configured via YAML files and can use any LangChain-compatible LLM provider.

## How It Works

- Agents execute sequentially as defined in `pipeline.yaml`
- Each agent can take input from pipeline input or other agents
- Multi-input agents supported (agent can read from multiple sources)
- All configuration via YAML files, no code changes needed
- Logs go to stderr (JSON format), structured output to stdout
- Exit codes: 0 = success, 1 = failure

## Structure

```
spec2code-naive/
├── main.py                    # CLI entry point
├── test_runtime.py            # Regression tests
├── test_config.py             # Config validation tool
├── core/
│   ├── agent.py               # Agent execution
│   └── orchestrator.py        # Pipeline orchestration
├── config/
│   ├── pipeline.yaml          # Agent sequence and inputs
│   ├── models/                # LLM provider configs
│   └── agents/                # Agent configs and prompts
└── config_system/
    └── config_loader.py       # Config loading and validation
```

## Usage

```bash
# Install dependencies
pip install -r requirements.txt
pip install langchain-openai  # or your preferred provider

# Set API key
export OPENAI_API_KEY="your-key"

# Run pipeline
python main.py -i sample_input.txt

# Test configuration
python test_config.py validate

# Run regression tests
python test_runtime.py

# CI/CD pipeline
python test_config.py validate && python test_runtime.py && python main.py -i input.txt
```

## Configuration

See `config/README.md` for configuration details.

## Multi-Input Agents

Agents can take input from multiple sources:

```yaml
agents:
  - name: "analyzer"
    inputs: ["pipeline_input"]           # Single input
  - name: "validator" 
    inputs: ["analyzer"]                 # Single agent input
  - name: "combiner"
    inputs: ["analyzer", "validator"]    # Multi-agent inputs
```

## Shared Data Structure

Pipeline maintains unified data context:

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

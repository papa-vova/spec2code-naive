"""
Agent factory for creating agent instances from configuration.
Separates config loading from agent instantiation.
"""
import importlib
from typing import Dict, Any, Optional
from langchain_core.language_models.base import BaseLanguageModel

from config_system.config_loader import ConfigLoader, ConfigValidationError, ModelConfig, AgentConfig


class ModelRegistry:
    """Registry for dynamic model provider imports."""
    
    _providers = {
        "openai-chat": {
            "import_path": "langchain_openai",
            "class_name": "ChatOpenAI"
        },
        # Add more providers as needed
        # "anthropic-chat": {
        #     "import_path": "langchain_anthropic", 
        #     "class_name": "ChatAnthropic"
        # },
        # "ollama-chat": {
        #     "import_path": "langchain_ollama",
        #     "class_name": "ChatOllama"
        # }
    }
    
    @classmethod
    def create_llm(cls, model_config: ModelConfig) -> BaseLanguageModel:
        """Create an LLM instance from model configuration."""
        provider_info = cls._providers.get(model_config._type)
        if not provider_info:
            raise ConfigValidationError(f"Unsupported model type: {model_config._type}")
        
        try:
            # Dynamic import
            module = importlib.import_module(provider_info["import_path"])
            llm_class = getattr(module, provider_info["class_name"])
            
            # Create LLM instance based on type
            if model_config._type == "openai-chat":
                return cls._create_openai_llm(llm_class, model_config)
            else:
                raise ConfigValidationError(f"LLM creation not implemented for type: {model_config._type}")
                
        except ImportError as e:
            provider_name = model_config._type.split("-")[0]
            raise ConfigValidationError(
                f"Model provider '{model_config._type}' requires additional dependencies. "
                f"Install with: pip install langchain-{provider_name}"
            )
        except Exception as e:
            raise ConfigValidationError(f"Failed to create LLM {model_config.name}: {str(e)}")
    
    @classmethod
    def _create_openai_llm(cls, llm_class, model_config: ModelConfig):
        """Create OpenAI LLM with proper parameter handling."""
        import os
        
        # Expand environment variables in API key
        api_key = model_config.openai_api_key or ""
        if api_key.startswith("${") and api_key.endswith("}"):
            env_var = api_key[2:-1]
            api_key = os.getenv(env_var)
            if not api_key:
                raise ConfigValidationError(f"Environment variable {env_var} not set for OpenAI API key")
        
        return llm_class(
            model=model_config.model_name or "gpt-4",
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
            top_p=model_config.top_p,
            api_key=api_key,
            streaming=model_config.streaming
        )


class AgentRegistry:
    """Registry for dynamic agent class imports."""
    
    _agents = {
        "plan_maker": {
            "import_path": "agents.plan_maker",
            "class_name": "PlanMakerAgent"
        },
        "plan_critique_generator": {
            "import_path": "agents.plan_critique_generator", 
            "class_name": "ReportGeneratorAgent"
        },
        "plan_critique_comparator": {
            "import_path": "agents.plan_critique_comparator",
            "class_name": "MetricComparatorAgent"
        }
    }
    
    @classmethod
    def create_agent(cls, agent_name: str, agent_config: AgentConfig, llm: Optional[BaseLanguageModel], dry_run: bool):
        """Create an agent instance from configuration."""
        agent_info = cls._agents.get(agent_name)
        if not agent_info:
            raise ConfigValidationError(f"Unknown agent type: {agent_name}")
        
        try:
            # Dynamic import
            module = importlib.import_module(agent_info["import_path"])
            agent_class = getattr(module, agent_info["class_name"])
            
            # Create agent instance based on type
            if agent_name == "plan_maker":
                return agent_class(llm=llm, dry_run=dry_run)
            elif agent_name == "plan_critique_generator":
                # For now, create single instance - multi-instance logic deferred
                from agents.plan_critique_generator import ReportType
                return agent_class(report_type=ReportType.TECHNICAL_FEASIBILITY, llm=llm, dry_run=dry_run)
            elif agent_name == "plan_critique_comparator":
                # MetricComparatorAgent doesn't need LLM for now (will be LLM-based later)
                return agent_class()
            else:
                raise ConfigValidationError(f"Agent instantiation not implemented for: {agent_name}")
                
        except ImportError as e:
            raise ConfigValidationError(f"Failed to import agent {agent_name}: {str(e)}")
        except Exception as e:
            raise ConfigValidationError(f"Failed to create agent {agent_name}: {str(e)}")


class AgentFactory:
    """Factory for creating agent instances from configuration."""
    
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.model_registry = ModelRegistry()
        self.agent_registry = AgentRegistry()
    
    def create_agent(self, agent_name: str, dry_run: bool = False):
        """Create a single agent instance from configuration."""
        # Load agent configuration
        agent_config = self.config_loader.load_agent_config(agent_name)
        
        # Create LLM if not in dry-run mode
        llm = None
        if not dry_run:
            model_config = self.config_loader.load_model_config(agent_config.llm)
            llm = self.model_registry.create_llm(model_config)
        
        # Create the agent
        return self.agent_registry.create_agent(agent_name, agent_config, llm, dry_run)
    
    def create_agents(self, required_agents: list, dry_run: bool = False) -> Dict[str, Any]:
        """Create multiple agents from a list of required agent names."""
        agents = {}
        for agent_name in required_agents:
            agents[agent_name] = self.create_agent(agent_name, dry_run)
        return agents

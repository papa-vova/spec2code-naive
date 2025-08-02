"""
Agent factory for creating agent instances from configuration.
Separates config loading from agent instantiation.
"""
import importlib
import os
from typing import Dict, Any, Optional
from langchain_core.language_models.base import BaseLanguageModel

from config_system.config_loader import ConfigLoader, ConfigValidationError, ModelConfig, AgentConfig
from core.agent import Agent


class ModelRegistry:
    """Fully dynamic registry for any LangChain model provider."""
    
    @classmethod
    def create_llm(cls, model_config: ModelConfig) -> BaseLanguageModel:
        """Create an LLM instance from model configuration using dynamic discovery."""
        try:
            # Package import must be lowercase
            provider_lowercase = model_config.provider.lower()
            module = importlib.import_module(f"langchain_{provider_lowercase}")
            
            # Class name uses the provider name as given in config
            class_name = f"Chat{model_config.provider}"
            
            llm_class = getattr(module, class_name)
            
            # Create LLM instance with generic parameter handling
            return cls._create_llm_instance(llm_class, model_config)
                
        except ImportError as e:
            raise ConfigValidationError(
                f"Model provider '{model_config.provider}' requires additional dependencies. "
                f"Install with: pip install langchain-{provider_lowercase}\n"
                f"Error: {str(e)}"
            )
        except AttributeError as e:
            raise ConfigValidationError(
                f"Provider '{model_config.provider}' does not have expected class '{class_name}'. "
                f"Error: {str(e)}"
            )
        except Exception as e:
            raise ConfigValidationError(f"Failed to create LLM {model_config.name}: {str(e)}")
    
    @classmethod
    def _create_llm_instance(cls, llm_class, model_config: ModelConfig):
        """Create LLM instance with generic parameter and credential handling."""
        # Start with model name
        llm_params = {"model": model_config.model_name}
        
        # Add all generic parameters
        llm_params.update(model_config.parameters)
        
        # Handle credentials with environment variable expansion
        for cred_key, cred_value in model_config.credentials.items():
            if cred_value.startswith("${") and cred_value.endswith("}"):
                env_var = cred_value[2:-1]
                expanded_value = os.getenv(env_var)
                if not expanded_value:
                    raise ConfigValidationError(f"Environment variable {env_var} not set for credential {cred_key}")
                llm_params[cred_key] = expanded_value
            else:
                llm_params[cred_key] = cred_value
        
        return llm_class(**llm_params)


# AgentRegistry removed - we now use the unified Agent class directly


class AgentFactory:
    """Factory for creating agent instances from configuration."""
    
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.model_registry = ModelRegistry()
    
    def create_agent(self, agent_name: str, dry_run: bool = False) -> Agent:
        """Create a single agent instance from configuration."""
        # Load agent and prompts configuration
        agent_config = self.config_loader.load_agent_config(agent_name)
        prompts_config = self.config_loader.load_prompts_config(agent_name)
        
        # Create LLM if not in dry-run mode
        llm = None
        if not dry_run:
            model_config = self.config_loader.load_model_config(agent_config.llm)
            llm = self.model_registry.create_llm(model_config)
        
        # Create the agent using the new Agent class
        return Agent(
            config=agent_config,
            prompts=prompts_config,
            llm=llm,
            dry_run=dry_run
        )
    
    def create_agents(self, required_agents: list, dry_run: bool = False) -> Dict[str, Any]:
        """Create multiple agents from a list of required agent names."""
        agents = {}
        for agent_name in required_agents:
            agents[agent_name] = self.create_agent(agent_name, dry_run)
        return agents

"""
Configuration loading and validation system for LangChain agents.
Uses standard LangChain terminology and patterns.
"""
import yaml
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from pydantic import BaseModel, ValidationError
from langchain.schema import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


class ModelConfig(BaseModel):
    """Configuration for LangChain LLM models."""
    name: str
    _type: str
    model_name: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    openai_api_key: Optional[str] = None
    streaming: bool = False


class ToolConfig(BaseModel):
    """Configuration for LangChain tools."""
    name: str
    description: str
    _type: str
    base_path: Optional[str] = None


class MemoryConfig(BaseModel):
    """Configuration for LangChain memory."""
    _type: str = "buffer"
    max_token_limit: int = 2000


class AgentConfig(BaseModel):
    """Configuration for LangChain agents."""
    name: str
    description: str
    llm: str
    tools: List[ToolConfig]
    memory: MemoryConfig
    agent_type: str = "zero-shot-react-description"
    max_iterations: int = 3
    early_stopping_method: str = "generate"


class PromptsConfig(BaseModel):
    """Configuration for agent prompts using LangChain message types."""
    system_message: str
    human_message_template: str
    ai_message_prefix: Optional[str] = None
    prompt_templates: Dict[str, str] = {}


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigLoader:
    """Loads and validates configuration files for LangChain agents."""
    
    def __init__(self, config_root: str = "./config"):
        self.config_root = Path(config_root)
        self._models_cache: Dict[str, ModelConfig] = {}
        self._agents_cache: Dict[str, AgentConfig] = {}
        self._prompts_cache: Dict[str, PromptsConfig] = {}
        
    def validate_config_structure(self) -> bool:
        """Validate that required config directories and files exist."""
        required_dirs = [
            self.config_root / "models",
            self.config_root / "agents"
        ]
        
        for dir_path in required_dirs:
            if not dir_path.exists():
                raise ConfigValidationError(f"Required config directory missing: {dir_path}")
        
        # Check for at least one model config
        model_files = list((self.config_root / "models").glob("*.yaml"))
        if not model_files:
            raise ConfigValidationError("No model configuration files found in config/models/")
            
        return True
    
    def load_model_config(self, model_name: str) -> ModelConfig:
        """Load and validate model configuration."""
        if model_name in self._models_cache:
            return self._models_cache[model_name]
            
        model_path = self.config_root / "models" / f"{model_name}.yaml"
        if not model_path.exists():
            raise ConfigValidationError(f"Model config not found: {model_path}")
            
        try:
            with open(model_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            model_config = ModelConfig(**config_data)
            self._models_cache[model_name] = model_config
            return model_config
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {model_path}: {e}")
        except ValidationError as e:
            raise ConfigValidationError(f"Invalid model config in {model_path}: {e}")
    
    def load_agent_config(self, agent_name: str) -> AgentConfig:
        """Load and validate agent configuration."""
        if agent_name in self._agents_cache:
            return self._agents_cache[agent_name]
            
        agent_dir = self.config_root / "agents" / agent_name
        agent_path = agent_dir / "agent.yaml"
        
        if not agent_path.exists():
            raise ConfigValidationError(f"Agent config not found: {agent_path}")
            
        try:
            with open(agent_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            agent_config = AgentConfig(**config_data)
            
            # Validate that referenced model exists
            self.load_model_config(agent_config.llm)
            
            self._agents_cache[agent_name] = agent_config
            return agent_config
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {agent_path}: {e}")
        except ValidationError as e:
            raise ConfigValidationError(f"Invalid agent config in {agent_path}: {e}")
    
    def load_prompts_config(self, agent_name: str) -> PromptsConfig:
        """Load and validate prompts configuration for an agent."""
        if agent_name in self._prompts_cache:
            return self._prompts_cache[agent_name]
            
        prompts_path = self.config_root / "agents" / agent_name / "prompts.yaml"
        
        if not prompts_path.exists():
            raise ConfigValidationError(f"Prompts config not found: {prompts_path}")
            
        try:
            with open(prompts_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            prompts_config = PromptsConfig(**config_data)
            self._prompts_cache[agent_name] = prompts_config
            return prompts_config
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {prompts_path}: {e}")
        except ValidationError as e:
            raise ConfigValidationError(f"Invalid prompts config in {prompts_path}: {e}")
    
    def create_chat_prompt_template(self, agent_name: str, template_name: str = "default") -> ChatPromptTemplate:
        """Create LangChain ChatPromptTemplate from configuration."""
        prompts_config = self.load_prompts_config(agent_name)
        
        messages = [
            SystemMessagePromptTemplate.from_template(prompts_config.system_message),
            HumanMessagePromptTemplate.from_template(prompts_config.human_message_template)
        ]
        
        if prompts_config.ai_message_prefix:
            # Add AI message prefix if specified
            messages.append(AIMessage(content=prompts_config.ai_message_prefix))
        
        return ChatPromptTemplate.from_messages(messages)
    
    def get_prompt_template(self, agent_name: str, template_name: str) -> str:
        """Get a specific prompt template by name."""
        prompts_config = self.load_prompts_config(agent_name)
        
        if template_name in prompts_config.prompt_templates:
            return prompts_config.prompt_templates[template_name]
        elif template_name == "default":
            return prompts_config.human_message_template
        else:
            raise ConfigValidationError(f"Prompt template '{template_name}' not found for agent '{agent_name}'")
    
    def list_available_models(self) -> List[str]:
        """List all available model configurations."""
        models_dir = self.config_root / "models"
        return [f.stem for f in models_dir.glob("*.yaml")]
    
    def list_available_agents(self) -> List[str]:
        """List all available agent configurations."""
        agents_dir = self.config_root / "agents"
        return [d.name for d in agents_dir.iterdir() if d.is_dir()]
    
    def validate_all_configs(self) -> bool:
        """Validate all configuration files."""
        try:
            self.validate_config_structure()
            
            # Validate all models
            for model_name in self.list_available_models():
                self.load_model_config(model_name)
            
            # Validate all agents and their prompts
            for agent_name in self.list_available_agents():
                self.load_agent_config(agent_name)
                self.load_prompts_config(agent_name)
            
            return True
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"Unexpected error during validation: {e}")


def validate_config(config_root: str = "./config") -> bool:
    """Validate configuration and raise exception if invalid."""
    loader = ConfigLoader(config_root)
    return loader.validate_all_configs()

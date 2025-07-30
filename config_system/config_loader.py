"""
Configuration loading and validation system for LangChain agents.
Uses standard LangChain terminology and patterns.
"""
import yaml
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, ValidationError
from langchain.schema import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate, ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


class ModelConfig(BaseModel):
    """Configuration for LangChain LLM models - fully generic."""
    name: str
    provider: str  # e.g., "openai", "anthropic", "ollama"
    model_name: str  # e.g., "gpt-4", "claude-3-sonnet", "llama2"
    parameters: Dict[str, Any] = {}  # Generic parameters like temperature, max_tokens, etc.
    credentials: Dict[str, str] = {}  # Generic credentials like api_key, etc.


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


class PipelineAgentConfig(BaseModel):
    """Configuration for a single agent in the pipeline."""
    name: str
    input_mapping: str
    output_key: str
    prompt_templates: Optional[Union[str, List[str]]] = None
    
    def get_template_names(self, available_templates: List[str]) -> List[str]:
        """Get normalized list of template names. If None/empty, return all available templates."""
        if not self.prompt_templates:
            # If missing or empty, use all available templates
            return available_templates
        elif isinstance(self.prompt_templates, str):
            # Single template as string
            return [self.prompt_templates]
        else:
            # Already a list
            return self.prompt_templates


class PipelineExecutionConfig(BaseModel):
    """Configuration for pipeline execution settings."""
    mode: str = "sequential"


class PipelineSettingsConfig(BaseModel):
    """Configuration for pipeline-level settings."""
    log_level: str = "INFO"


class PipelineConfig(BaseModel):
    """Configuration for the entire pipeline."""
    name: str
    description: str
    agents: List[PipelineAgentConfig]
    execution: PipelineExecutionConfig
    settings: PipelineSettingsConfig


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
            
            # Validate that all non-prompt_templates have exactly one option
            self._validate_prompts_structure(prompts_config, agent_name)
            
            self._prompts_cache[agent_name] = prompts_config
            return prompts_config
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {prompts_path}: {e}")
        except ValidationError as e:
            raise ConfigValidationError(f"Invalid prompts config in {prompts_path}: {e}")
    
    def load_pipeline_config(self) -> PipelineConfig:
        """Load and validate pipeline configuration."""
        pipeline_path = self.config_root / "pipeline.yaml"
        
        if not pipeline_path.exists():
            raise ConfigValidationError(f"Pipeline config not found: {pipeline_path}")
            
        try:
            with open(pipeline_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Extract the pipeline section
            if 'pipeline' not in config_data:
                raise ConfigValidationError("Pipeline config must have a 'pipeline' section")
                
            pipeline_data = config_data['pipeline']
            pipeline_config = PipelineConfig(**pipeline_data)
            return pipeline_config
            
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {pipeline_path}: {e}")
        except ValidationError as e:
            raise ConfigValidationError(f"Invalid pipeline config in {pipeline_path}: {e}")

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
    
    def _validate_prompts_structure(self, prompts_config: PromptsConfig, agent_name: str) -> None:
        """Validate that all non-prompt_templates have exactly one option."""
        # Check system_message - must be a single string
        if isinstance(prompts_config.system_message, (list, dict)):
            raise ConfigValidationError(
                f"Agent '{agent_name}': system_message must be a single string, not {type(prompts_config.system_message).__name__}"
            )
        
        # Check human_message_template - must be a single string
        if isinstance(prompts_config.human_message_template, (list, dict)):
            raise ConfigValidationError(
                f"Agent '{agent_name}': human_message_template must be a single string, not {type(prompts_config.human_message_template).__name__}"
            )
        
        # Check ai_message_prefix - must be a single string or None
        if prompts_config.ai_message_prefix is not None and isinstance(prompts_config.ai_message_prefix, (list, dict)):
            raise ConfigValidationError(
                f"Agent '{agent_name}': ai_message_prefix must be a single string or None, not {type(prompts_config.ai_message_prefix).__name__}"
            )
        
        # prompt_templates can be a dict with multiple options - this is allowed
        # No validation needed for prompt_templates as it's designed to have multiple options
    
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
    
    def _validate_pipeline_template_consistency(self) -> None:
        """Validate pipeline configuration and template consistency."""
        try:
            pipeline_config = self.load_pipeline_config()
        except ConfigValidationError:
            # Pipeline config validation already failed, skip this check
            return
        
        for agent_config in pipeline_config.agents:
            agent_name = agent_config.name
            
            # Load agent's prompts config to get available templates
            try:
                prompts_config = self.load_prompts_config(agent_name)
            except ConfigValidationError as e:
                raise ConfigValidationError(f"Cannot validate pipeline templates for agent '{agent_name}': {e}")
            
            available_templates = list(prompts_config.prompt_templates.keys())
            
            # Get the templates this agent wants to use
            requested_templates = agent_config.get_template_names(available_templates)
            
            # Validate that all requested templates exist in the agent's prompts.yaml
            for template_name in requested_templates:
                if template_name not in available_templates:
                    raise ConfigValidationError(
                        f"Agent '{agent_name}' in pipeline.yaml references template '{template_name}' "
                        f"which does not exist in its prompts.yaml. Available templates: {available_templates}"
                    )
            
            # Ensure agent has at least one template available in prompts.yaml
            if not available_templates:
                raise ConfigValidationError(
                    f"Agent '{agent_name}' has no prompt_templates defined in its prompts.yaml. "
                    f"At least one template must be defined."
                )
    
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
            
            # Validate pipeline configuration and template consistency
            self._validate_pipeline_template_consistency()
            
            return True
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"Unexpected error during validation: {e}")
    



def validate_config(config_root: str = "./config") -> bool:
    """Validate configuration and raise exception if invalid."""
    loader = ConfigLoader(config_root)
    return loader.validate_all_configs()

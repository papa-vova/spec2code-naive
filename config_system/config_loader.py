"""
Configuration loading and validation system for LangChain agents.
Uses standard LangChain terminology and patterns.
"""
import yaml
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


class ModelConfig(BaseModel):
    """Configuration for LangChain LLM models - fully generic."""
    name: str
    provider: str  # e.g., "openai", "anthropic", "ollama"
    model_name: str  # e.g., "gpt-4", "claude-3-sonnet", "llama2"
    parameters: Dict[str, Any] = {}  # Generic parameters like temperature, max_tokens, etc.
    credentials: Dict[str, str] = {}  # Generic credentials like api_key, etc.


# ToolConfig and MemoryConfig classes removed as they are no longer used


class AgentConfig(BaseModel):
    """Configuration for LangChain agents."""
    name: str
    description: str
    llm: str


class PromptsConfig(BaseModel):
    """Configuration for agent prompts using LangChain message types."""
    system_message: str
    human_message_template: str
    ai_message_prefix: Optional[str] = None
    prompt_templates: Optional[Union[str, Dict[str, str]]] = None


class PipelineAgentConfig(BaseModel):
    """Configuration for a single agent in the pipeline."""
    name: str
    inputs: List[str]  # List of agent names or "pipeline_input"
    prompt_templates: Optional[Union[str, List[str]]] = None
    
    def get_template_names(self, available_templates: List[str]) -> List[str]:
        """Get normalized list of template names based on configuration:
        1. prompt_templates absent/empty → use all available templates (or empty if none)
        2. prompt_templates has single string → use that template name
        3. prompt_templates has list → use specified template names
        """
        if not self.prompt_templates:
            # Case 1: No prompt_templates specified → use all available templates
            return available_templates
        elif isinstance(self.prompt_templates, str):
            # Case 2: Single template name as string
            return [self.prompt_templates]
        else:
            # Case 3: Multiple template names as list
            return self.prompt_templates


class PipelineExecutionConfig(BaseModel):
    """Configuration for pipeline execution settings."""
    mode: str = "sequential"


class PipelineSettingsConfig(BaseModel):
    """Configuration for pipeline-level settings."""
    log_level: str = "INFO"
    # Run management settings
    create_run_artifacts: bool = True
    include_messages_in_artifacts: bool = False
    runs_directory: str = "runs"


class PipelineConfig(BaseModel):
    """Configuration for the entire pipeline."""
    name: str
    description: str
    agents: List[PipelineAgentConfig]
    execution: PipelineExecutionConfig
    settings: PipelineSettingsConfig


class RoleModelProfile(BaseModel):
    """Role-level model profile."""

    model: str


class AuditConfig(BaseModel):
    """Configuration for audit gates and sufficiency policies."""

    min_confidence_to_proceed: float = 0.6
    min_input_size_for_sufficiency: int = 120
    insufficient_markers: List[str] = Field(default_factory=lambda: ["TBD", "TODO"])
    sufficiency_rubric: Optional[str] = None


class AgenticConfig(BaseModel):
    """Configuration for agentic role model profiles and audit policy."""

    role_model_profiles: Dict[str, RoleModelProfile]
    audit: AuditConfig = Field(default_factory=AuditConfig)


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
        self._agentic_config: Optional[AgenticConfig] = None
        
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

    def load_agentic_config(self) -> AgenticConfig:
        """Load and validate agentic configuration."""
        if self._agentic_config is not None:
            return self._agentic_config

        agentic_path = self.config_root / "agentic.yaml"
        if not agentic_path.exists():
            raise ConfigValidationError(f"Agentic config not found: {agentic_path}")

        try:
            with open(agentic_path, "r", encoding="utf-8") as file_obj:
                config_data = yaml.safe_load(file_obj) or {}
            agentic_config = AgenticConfig(**config_data)

            # Ensure referenced model profiles are resolvable.
            for role_name, profile in agentic_config.role_model_profiles.items():
                try:
                    self.load_model_config(profile.model)
                except ConfigValidationError as exc:
                    raise ConfigValidationError(
                        f"Role profile '{role_name}' references invalid model '{profile.model}': {exc}"
                    ) from exc

            self._agentic_config = agentic_config
            return agentic_config
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {agentic_path}: {e}")
        except ValidationError as e:
            raise ConfigValidationError(f"Invalid agentic config in {agentic_path}: {e}")

    def get_role_model(self, role_name: str) -> str:
        """Resolve model name configured for a role."""
        agentic = self.load_agentic_config()
        if role_name not in agentic.role_model_profiles:
            raise ConfigValidationError(f"Role model profile not found for role: {role_name}")
        return agentic.role_model_profiles[role_name].model

    def get_audit_config(self) -> AuditConfig:
        """Resolve configured audit policy."""
        return self.load_agentic_config().audit

    def get_min_confidence_to_proceed(self) -> float:
        """Resolve confidence threshold for orchestrator stop/proceed decisions."""
        return self.get_audit_config().min_confidence_to_proceed

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
        """Get a specific prompt template by name or content."""
        prompts_config = self.load_prompts_config(agent_name)
        
        # Handle the three valid cases for prompt_templates
        if prompts_config.prompt_templates is None:
            # Case 1: Missing/empty prompt_templates - should not be called for templates
            raise ConfigValidationError(f"No prompt templates defined for agent '{agent_name}'")
        elif isinstance(prompts_config.prompt_templates, str):
            # Case 2: Unnamed template content - this method should never be called for Case 2
            raise ConfigValidationError(f"Agent '{agent_name}' has unnamed template content. This should be handled directly by the orchestrator, not through template name resolution.")
        elif isinstance(prompts_config.prompt_templates, dict):
            # Case 3: Named templates dictionary
            if template_name in prompts_config.prompt_templates:
                return prompts_config.prompt_templates[template_name]
            else:
                available_templates = list(prompts_config.prompt_templates.keys())
                raise ConfigValidationError(f"Prompt template '{template_name}' not found for agent '{agent_name}'. Available: {available_templates}")
        else:
            raise ConfigValidationError(f"Invalid prompt_templates format for agent '{agent_name}'")
    
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
            
            # Initialize available_templates list
            available_templates = []
            
            # Handle the three valid cases for prompt_templates
            if prompts_config.prompt_templates is None:
                # Case 1: Missing/empty prompt_templates - only human_message_template used
                pass
            elif isinstance(prompts_config.prompt_templates, str):
                # Case 2: Unnamed template content - pipeline.yaml should not specify templates
                # The unnamed template will be used automatically
                if agent_config.prompt_templates is not None:
                    raise ConfigValidationError(
                        f"Agent '{agent_name}' has unnamed template content in prompts.yaml, "
                        f"but pipeline.yaml specifies prompt_templates. For unnamed templates, "
                        f"leave prompt_templates empty/absent in pipeline.yaml."
                    )
                # For string templates, we have one unnamed template available
                available_templates = ["unnamed_template"]
            elif isinstance(prompts_config.prompt_templates, dict):
                # Case 3: Named templates dictionary - validate specific template names
                available_templates = list(prompts_config.prompt_templates.keys())
                
                # Get the templates this agent wants to use
                requested_templates = agent_config.get_template_names(available_templates)
                
                # Validate that all requested templates exist
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

            # Validate agentic role model profiles if config file exists
            agentic_path = self.config_root / "agentic.yaml"
            if agentic_path.exists():
                self.load_agentic_config()
            
            return True
            
        except ConfigValidationError:
            raise
        except Exception as e:
            raise ConfigValidationError(f"Unexpected error during validation: {e}")
    



def validate_config(config_root: str = "./config") -> bool:
    """Validate configuration and raise exception if invalid."""
    loader = ConfigLoader(config_root)
    return loader.validate_all_configs()

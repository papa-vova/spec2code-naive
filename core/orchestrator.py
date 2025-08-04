"""
Configuration-driven orchestrator for executing agent pipelines.
Replaces hardcoded pipeline logic with configurable agent sequences.
"""
import json
import time
from typing import Dict, Any, Optional

from config_system.config_loader import ConfigLoader, PipelineConfig
from config_system.agent_factory import AgentFactory
from core.agent import Agent
from exceptions import PipelineError
from logging_config import log_step_start, log_step_complete, log_error, log_debug


class Orchestrator:
    """Configuration-driven orchestrator for agent pipeline execution."""
    
    def __init__(self, config_root: str = "./config", dry_run: bool = False):
        """Initialize orchestrator with configuration."""
        self.config_root = config_root
        self.dry_run = dry_run
        self.logger = None
        
        # Initialize config system
        self.config_loader = ConfigLoader(config_root)
        self.agent_factory = AgentFactory(self.config_loader)
        
        # Load pipeline configuration
        self.pipeline_config = self.config_loader.load_pipeline_config()
        
        # Validate pipeline configuration
        self._validate_pipeline_config()
    
    def set_logger(self, logger):
        """Set logger for this orchestrator instance."""
        self.logger = logger
    
    def _validate_pipeline_config(self):
        """Validate that pipeline configuration is consistent."""
        if not self.pipeline_config.agents:
            raise PipelineError("Pipeline configuration must have at least one agent")
        
        # Validate that all referenced agents have configurations
        for agent_config in self.pipeline_config.agents:
            try:
                # Try to load agent config to ensure it exists
                self.config_loader.load_agent_config(agent_config.name)
                self.config_loader.load_prompts_config(agent_config.name)
            except Exception as e:
                raise PipelineError(f"Invalid agent reference '{agent_config.name}' in pipeline: {e}")
    
    def execute_pipeline(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the configured pipeline with given input data.
        
        Args:
            input_data: Initial input data for the pipeline
            
        Returns:
            Dictionary containing all intermediate results and final output
        """
        if self.logger:
            log_step_start(
                self.logger, 
                "Orchestrator", 
                "pipeline_execution", 
                f"Starting pipeline '{self.pipeline_config.name}' execution",
                {
                    "pipeline_name": self.pipeline_config.name,
                    "agent_count": len(self.pipeline_config.agents),
                    "execution_mode": self.pipeline_config.execution.mode
                }
            )
        
        # Initialize pipeline data storage with unified structure
        pipeline_start_time = time.time()
        pipeline_data = {
            "pipeline_input": input_data,  # Store original input
            "agents": {},  # Store each agent's output and metadata
            "metadata": {
                "agent_sequence": [agent.name for agent in self.pipeline_config.agents]
            }
        }
        
        try:
            # Execute agents in sequence
            for i, agent_config in enumerate(self.pipeline_config.agents):
                agent_start_time = time.time()
                
                if self.logger:
                    log_step_start(
                        self.logger,
                        "Orchestrator",
                        f"agent_{agent_config.name}",
                        f"Executing agent {i+1}/{len(self.pipeline_config.agents)}: {agent_config.name}",
                        {
                            "agent_name": agent_config.name,
                            "input_sources": agent_config.inputs,
                            "prompt_templates": agent_config.prompt_templates
                        }
                    )
                
                # Create agent instance
                agent = self._create_agent(agent_config.name)
                
                # Prepare input data for this agent
                agent_input = self._prepare_agent_input(pipeline_data, agent_config)
                
                # Execute agent with specified templates
                agent_output = self._execute_agent(agent, agent_input, agent_config)
                
                # Store agent output in unified structure
                # Determine input sources format: 
                # - String "pipeline_input" only if SOLE input is pipeline_input
                # - Array for all other cases (multiple agents, or mixed pipeline_input + agents)
                if len(agent_config.inputs) == 1 and agent_config.inputs[0] == "pipeline_input":
                    input_sources = "pipeline_input"  # String for sole pipeline input
                else:
                    input_sources = agent_config.inputs  # Array for multiple/mixed inputs
                
                pipeline_data["agents"][agent_config.name] = {
                    "output": agent_output["output"],
                    "metadata": {
                        "execution_time": (time.time() - agent_start_time) * 1000,
                        "templates_used": agent_output.get("templates_used", []),
                        "input_sources": input_sources
                    }
                }
                
                if self.logger:
                    log_step_complete(
                        self.logger,
                        "Orchestrator",
                        f"agent_{agent_config.name}",
                        f"Agent {agent_config.name} completed successfully",
                        {
                            "agent_name": agent_config.name,
                            "output_keys": list(agent_output["output"].keys()) if isinstance(agent_output["output"], dict) else ["scalar"]
                        },
                        pipeline_data["agents"][agent_config.name]["metadata"]["execution_time"]
                    )
            
            # Prepare final result
            total_execution_time = (time.time() - pipeline_start_time) * 1000
            pipeline_data["metadata"]["execution_time"] = total_execution_time
        
            final_result = {
                "pipeline_name": self.pipeline_config.name,
                "execution_successful": True,
                "pipeline_input": pipeline_data["pipeline_input"],
                "agents": pipeline_data["agents"],
                "metadata": pipeline_data["metadata"]
            }
            
            if self.logger:
                log_step_complete(
                    self.logger,
                    "Orchestrator",
                    "pipeline_execution",
                    f"Pipeline '{self.pipeline_config.name}' completed successfully",
                    {
                        "agents_executed": len(self.pipeline_config.agents)
                    }
                )
            
            return final_result
            
        except Exception as e:
            if self.logger:
                log_error(self.logger, f"Pipeline execution failed: {str(e)}", "Orchestrator", e)
            raise PipelineError(f"Pipeline execution failed: {str(e)}")
    
    def _create_agent(self, agent_name: str) -> Agent:
        """Create an agent instance for the given agent name."""
        agent = self.agent_factory.create_agent(agent_name, self.dry_run)
        if self.logger:
            agent.set_logger(self.logger)
        return agent
    
    def _prepare_agent_input(self, pipeline_data: Dict[str, Any], agent_config) -> Dict[str, Any]:
        """Prepare input data for an agent based on its input sources."""
        if len(agent_config.inputs) == 1:
            # Single input - put directly in "input" key
            input_source = agent_config.inputs[0]
            if input_source == "pipeline_input":
                return {"input": pipeline_data["pipeline_input"]}
            elif input_source in pipeline_data["agents"]:
                return {"input": pipeline_data["agents"][input_source]["output"]}
            else:
                raise PipelineError(f"Invalid input source '{input_source}' for agent '{agent_config.name}'")
        else:
            # Multiple inputs - create dict with agent names as keys
            agent_input = {}
            for input_source in agent_config.inputs:
                if input_source == "pipeline_input":
                    agent_input[input_source] = pipeline_data["pipeline_input"]
                elif input_source in pipeline_data["agents"]:
                    agent_input[input_source] = pipeline_data["agents"][input_source]["output"]
                else:
                    raise PipelineError(f"Invalid input source '{input_source}' for agent '{agent_config.name}'")
            return {"input": agent_input}
    
    def _execute_agent(self, agent: Agent, agent_input: Dict[str, Any], agent_config) -> Dict[str, Any]:
        """Execute agent with specified prompt templates and aggregate results."""
        # Get available templates from agent's prompts config
        prompts_config = self.config_loader.load_prompts_config(agent_config.name)
        
        # Get include_messages_in_artifacts setting from pipeline config
        include_messages = self.pipeline_config.settings.include_messages_in_artifacts
        
        # Determine what templates to execute based on prompts.yaml content
        if prompts_config.prompt_templates is None:
            # Case 1: Missing/empty prompt_templates - only human_message_template
            result = agent.execute(agent_input, None, include_messages)  # None indicates no additional template
            result["templates_used"] = []
            return result
        elif isinstance(prompts_config.prompt_templates, str):
            # Case 2: Unnamed template content - execute both human_message_template and unnamed content
            # Execute with the unnamed template content directly
            result = agent.execute_with_unnamed_template(agent_input, prompts_config.prompt_templates, include_messages)
            result["templates_used"] = ["unnamed_template"]
            return result
        elif isinstance(prompts_config.prompt_templates, dict):
            # Case 3: Named templates dictionary - use what's specified in pipeline.yaml
            available_templates = list(prompts_config.prompt_templates.keys())
            template_list = agent_config.get_template_names(available_templates)
        else:
            template_list = []
        
        # Case 3: Multiple template execution
        aggregated_output = {
            "template_results": {},
            "execution_metadata": {
                "templates_used": template_list,
                "template_count": len(template_list)
            }
        }
        template_results = []  # Initialize list to collect template outputs
        
        for template_name in template_list:
            if self.logger:
                log_step_start(
                    self.logger,
                    agent_config.name,
                    f"template_{template_name}",
                    f"Executing {agent_config.name} with template '{template_name}'",
                    {"template_name": template_name}
                )
            
            # Execute agent with this specific template
            template_result = agent.execute(agent_input, template_name, include_messages)
            
            # Store individual template result
            aggregated_output["template_results"][template_name] = template_result["output"]
            template_results.append(template_result["output"])
            
            if self.logger:
                log_step_complete(
                    self.logger,
                    agent_config.name,
                    f"template_{template_name}",
                    f"Template '{template_name}' execution completed",
                    {"template_name": template_name}
                )
        

        
        # Return in standard agent output format
        return {
            "output": aggregated_output,
            "templates_used": template_list,
            "metadata": {
                "agent_name": agent_config.name,
                "multi_template_execution": True,
                "templates_executed": template_list
            }
        }

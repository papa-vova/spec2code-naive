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
        
        # Initialize pipeline data storage
        pipeline_data = {
            "pipeline_input": input_data,  # Store original input
            "agent_outputs": {},  # Store outputs from each agent
            "execution_metadata": {
                "pipeline_name": self.pipeline_config.name,
                "dry_run": self.dry_run,
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
                            "input_mapping": agent_config.input_mapping,
                            "output_key": agent_config.output_key,
                            "prompt_template": agent_config.prompt_template
                        }
                    )
                
                # Create agent instance
                agent = self._create_agent(agent_config.name)
                
                # Prepare input data for this agent
                agent_input = self._prepare_agent_input(pipeline_data, agent_config)
                
                # Execute agent
                agent_output = agent.execute(agent_input)
                
                # Store agent output
                pipeline_data["agent_outputs"][agent_config.name] = agent_output
                pipeline_data[agent_config.output_key] = agent_output["output"]
                
                agent_duration = (time.time() - agent_start_time) * 1000
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
                        agent_duration
                    )
            
            # Prepare final result
            final_result = {
                "pipeline_name": self.pipeline_config.name,
                "execution_successful": True,
                "final_output": pipeline_data[self.pipeline_config.agents[-1].output_key],
                "all_outputs": {agent.output_key: pipeline_data[agent.output_key] for agent in self.pipeline_config.agents},
                "metadata": pipeline_data["execution_metadata"]
            }
            
            if self.logger:
                log_step_complete(
                    self.logger,
                    "Orchestrator",
                    "pipeline_execution",
                    f"Pipeline '{self.pipeline_config.name}' completed successfully",
                    {
                        "agents_executed": len(self.pipeline_config.agents),
                        "final_output_type": type(final_result["final_output"]).__name__
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
        """Prepare input data for an agent based on its input mapping."""
        input_mapping = agent_config.input_mapping
        
        if input_mapping == "pipeline_input":
            # Use the original pipeline input
            input_data = pipeline_data["pipeline_input"]
        elif input_mapping in pipeline_data:
            # Use output from a previous agent
            input_data = pipeline_data[input_mapping]
        else:
            raise PipelineError(f"Invalid input mapping '{input_mapping}' for agent '{agent_config.name}'")
        
        # Wrap in standard format if it's not already
        if isinstance(input_data, dict) and "input" in input_data:
            return input_data
        else:
            return {"input": input_data}

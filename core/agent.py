"""
Generic Agent class that can be configured to behave as any agent type.
Replaces individual agent classes with a single configurable implementation.
"""
import json
from typing import Dict, Any, Optional
from langchain_core.language_models.base import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from config_system.config_loader import AgentConfig, PromptsConfig
from exceptions import PlanGenerationError, ReportGenerationError, MetricComparisonError
from logging_config import log_step_start, log_step_complete, log_error


class Agent:
    """Generic agent that can be configured to perform different roles."""
    
    def __init__(self, 
                 config: AgentConfig, 
                 prompts: PromptsConfig, 
                 llm: Optional[BaseLanguageModel] = None, 
                 dry_run: bool = False):
        """Initialize agent with configuration."""
        self.config = config
        self.prompts = prompts
        self.llm = llm
        self.dry_run = dry_run
        self.logger = None
    
    def set_logger(self, logger):
        """Set logger for this agent instance."""
        self.logger = logger
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent with given input data.
        
        Args:
            input_data: JSON input data
            
        Returns:
            JSON output data in format: {"output": {...}, "metadata": {...}}
        """
        if self.logger:
            log_step_start(
                self.logger, 
                self.config.name, 
                "execute", 
                f"Starting {self.config.name} execution",
                {"input_keys": list(input_data.keys())}
            )
        
        try:
            if self.dry_run:
                # In dry-run mode, return dummy output based on input
                output = {
                    "agent_response": f"DUMMY OUTPUT from {self.config.name}",
                    "processed_input": input_data.get("input", {}),
                    "agent_type": self.config.name
                }
            else:
                # Actual LangChain execution logic
                output = self._execute_with_langchain(input_data)
            
            result = {
                "output": output,
                "metadata": {
                    "agent_name": self.config.name,
                    "dry_run": self.dry_run,
                    "input_received": True
                }
            }
            
            if self.logger:
                log_step_complete(
                    self.logger,
                    self.config.name,
                    "execute", 
                    f"Completed {self.config.name} execution",
                    {"output_keys": list(result["output"].keys())}
                )
            
            return result
            
        except Exception as e:
            if self.logger:
                log_error(self.logger, f"Agent {self.config.name} execution failed: {str(e)}", self.config.name, e)
            raise
    
    def _execute_with_langchain(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent using actual LangChain with LLM and prompts.
        
        Args:
            input_data: JSON input data
            
        Returns:
            Processed output data
        """
        try:
            # Extract the main input content
            input_content = input_data.get("input", "")
            if isinstance(input_content, dict):
                # If input is a dict, convert to string representation
                input_content = str(input_content)
            
            # Build the LangChain prompt chain
            messages = []
            
            # Add system message if available
            if hasattr(self.prompts, 'system_message') and self.prompts.system_message:
                messages.append(SystemMessage(content=self.prompts.system_message))
            
            # Add human message with input data
            if hasattr(self.prompts, 'human_message_template') and self.prompts.human_message_template:
                # Format the human message template with input data
                human_content = self.prompts.human_message_template.format(
                    decomposed_steps=input_content,
                    input=input_content,
                    **input_data  # Allow any additional template variables
                )
                messages.append(HumanMessage(content=human_content))
            else:
                # Fallback: use input directly
                messages.append(HumanMessage(content=input_content))
            
            # Create the chain: LLM + output parser
            output_parser = StrOutputParser()
            chain = self.llm | output_parser
            
            # Execute the chain
            if self.logger:
                self.logger.debug(f"Executing LangChain for {self.config.name}", extra={
                    "component": self.config.name,
                    "data": {"message_count": len(messages)}
                })
            
            response = chain.invoke(messages)
            
            # Return structured output
            return {
                "agent_response": response,
                "processed_input": input_data.get("input", {}),
                "agent_type": self.config.name,
                "llm_used": True
            }
            
        except Exception as e:
            if self.logger:
                log_error(self.logger, f"LangChain execution failed for {self.config.name}: {str(e)}", self.config.name, e)
            # Fallback to basic output if LangChain fails
            return {
                "agent_response": f"Error in {self.config.name}: {str(e)}",
                "processed_input": input_data.get("input", {}),
                "agent_type": self.config.name,
                "llm_used": False,
                "error": str(e)
            }


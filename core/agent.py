"""
Generic Agent class that can be configured to behave as any agent type.
Replaces individual agent classes with a single configurable implementation.
"""
import json
from typing import Dict, Any, Optional
from langchain_core.language_models.base import BaseLanguageModel
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
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
    
    def execute(self, input_data: Dict[str, Any], template_name: str, include_messages_in_artifacts: bool = False) -> Dict[str, Any]:
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
                    "agent_response": f"DUMMY OUTPUT from {self.config.name}"
                }
            else:
                # Actual LangChain execution logic
                output = self._execute_template(input_data, template_name, include_messages_in_artifacts)
            
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
    
    def execute_with_unnamed_template(self, input_data: Dict[str, Any], unnamed_template_content: str, include_messages_in_artifacts: bool = False) -> Dict[str, Any]:
        """
        Execute the agent with unnamed template content (Case 2).
        
        Args:
            input_data: JSON input data
            unnamed_template_content: The actual template content string
            
        Returns:
            JSON output data in format: {"output": {...}, "metadata": {...}}
        """
        if self.logger:
            log_step_start(
                self.logger, 
                self.config.name, 
                "execute_unnamed", 
                f"Starting {self.config.name} execution with unnamed template",
                {"input_keys": list(input_data.keys())}
            )
        
        try:
            if self.dry_run:
                # In dry-run mode, return dummy output based on input
                output = {
                    "agent_response": f"DUMMY OUTPUT from {self.config.name} with unnamed template"
                }
            else:
                # Actual LangChain execution logic with unnamed template
                output = self._execute_with_unnamed_template(input_data, unnamed_template_content, include_messages_in_artifacts)
            
            result = {
                "output": output,
                "metadata": {
                    "agent_name": self.config.name,
                    "dry_run": self.dry_run,
                    "input_received": True,
                    "unnamed_template_used": True
                }
            }
            
            if self.logger:
                log_step_complete(
                    self.logger,
                    self.config.name,
                    "execute_unnamed", 
                    f"Completed {self.config.name} execution with unnamed template",
                    {"output_keys": list(result["output"].keys())}
                )
            
            return result
            
        except Exception as e:
            if self.logger:
                log_error(self.logger, f"Agent {self.config.name} execution with unnamed template failed: {str(e)}", self.config.name, e)
            raise
    
    def _execute_with_unnamed_template(self, input_data: Dict[str, Any], unnamed_template_content: str, include_messages_in_artifacts: bool = False) -> Dict[str, Any]:
        """
        Execute the agent using LangChain with unnamed template content (Case 2).
        Instantiates both human_message_template AND the unnamed template content.
        
        Args:
            input_data: JSON input data
            unnamed_template_content: The actual template content string
            
        Returns:
            Processed output data
        """
        try:
            # Extract the raw input content - this will be used for {input}
            # This is the special case for {input} which always represents the raw input
            raw_input = input_data.get("input", "")
            
            # Create format_vars dictionary, starting with the raw input
            # Remove "input" from input_data to prevent duplicate keys when merging
            format_vars = {"input": raw_input}
            
            # Add all other fields from input_data except "input" to avoid duplicates
            filtered_input_data = {k: v for k, v in input_data.items() if k != "input"}
            
            # Build the LangChain prompt chain with proper message types and roles
            messages = []
            
            # 1. Add system message (AI instructions/context)
            if hasattr(self.prompts, 'system_message') and self.prompts.system_message:
                messages.append(SystemMessage(content=self.prompts.system_message))
            
            # 2. Add human message template (ALWAYS included)
            if hasattr(self.prompts, 'human_message_template') and self.prompts.human_message_template:
                # Format with all variables, where {input} is the raw input and other fields come from input_data
                human_content = self.prompts.human_message_template.format(**format_vars, **filtered_input_data)
                messages.append(HumanMessage(content=human_content))

            # 3. Add the unnamed template content (Case 2 specific)
            # Format with all variables, where {input} is the raw input and other fields come from input_data
            unnamed_content = unnamed_template_content.format(**format_vars, **filtered_input_data)
            messages.append(HumanMessage(content=unnamed_content))

            # 4. Add AI message prefix if available (optional AI response starter)
            if hasattr(self.prompts, 'ai_message_prefix') and self.prompts.ai_message_prefix:
                messages.append(AIMessage(content=self.prompts.ai_message_prefix))

            # Create the chain: LLM + output parser
            output_parser = StrOutputParser()
            chain = self.llm | output_parser
            
            # Execute the chain
            if self.logger:
                self.logger.debug(f"Executing LangChain for {self.config.name} with unnamed template", extra={
                    "component": self.config.name,
                    "data": {"message_count": len(messages)}
                })
            
            response = chain.invoke(messages)
            
            # Debug logging to understand the response format
            if self.logger:
                self.logger.debug(f"Raw LLM response for {self.config.name}: {repr(response)}", extra={
                    "component": self.config.name,
                    "data": {"response_type": type(response).__name__, "response_length": len(str(response))}
                })
            
            # Return structured output with optional message capture
            result = {
                "agent_response": response,
                "llm_used": True
            }
            
            # Capture messages if requested
            if include_messages_in_artifacts:
                result["messages"] = [
                    {
                        "type": "system" if isinstance(msg, SystemMessage) else 
                                "human" if isinstance(msg, HumanMessage) else 
                                "ai" if isinstance(msg, AIMessage) else "unknown",
                        "content": msg.content
                    }
                    for msg in messages
                ]
            
            return result
            
        except Exception as e:
            if self.logger:
                log_error(self.logger, f"LangChain execution with unnamed template failed for {self.config.name}: {str(e)}", self.config.name, e)
            # Fallback to basic output if LangChain fails
            return {
                "agent_response": f"Error in {self.config.name}: {str(e)}",
                "llm_used": False,
                "error": str(e)
            }
    
    def _execute_template(self, input_data: Dict[str, Any], template_name: str, include_messages_in_artifacts: bool = False) -> Dict[str, Any]:
        """
        Execute the agent using actual LangChain with LLM and prompts.
        
        Args:
            input_data: JSON input data
            template_name: Name of the template to use
            include_messages_in_artifacts: Whether to capture messages in output
            
        Returns:
            Processed output data
        """
        try:
            # Extract the raw input content - this will be used for {input}
            # This is the special case for {input} which always represents the raw input
            raw_input = input_data.get("input", "")
            
            # Create format_vars dictionary, starting with the raw input
            # Remove "input" from input_data to prevent duplicate keys when merging
            format_vars = {"input": raw_input}
            
            # Add all other fields from input_data except "input" to avoid duplicates
            filtered_input_data = {k: v for k, v in input_data.items() if k != "input"}
            
            # Build the LangChain prompt chain with proper message types and roles
            messages = []
            
            # 1. Add system message (AI instructions/context)
            if hasattr(self.prompts, 'system_message') and self.prompts.system_message:
                messages.append(SystemMessage(content=self.prompts.system_message))
            
            # 2. Add human message template (ALWAYS included)
            if hasattr(self.prompts, 'human_message_template') and self.prompts.human_message_template:
                # Format with all variables, where {input} is the raw input and other fields come from input_data
                human_content = self.prompts.human_message_template.format(**format_vars, **filtered_input_data)
                messages.append(HumanMessage(content=human_content))

            # 3. Add specific prompt template if available and specified
            if template_name is not None and hasattr(self.prompts, 'prompt_templates') and self.prompts.prompt_templates and template_name in self.prompts.prompt_templates:
                # Format with all variables, where {input} is the raw input and other fields come from input_data
                template_content = self.prompts.prompt_templates[template_name].format(**format_vars, **filtered_input_data)
                messages.append(HumanMessage(content=template_content))

            # 4. Add AI message prefix if available (optional AI response starter)
            if hasattr(self.prompts, 'ai_message_prefix') and self.prompts.ai_message_prefix:
                messages.append(AIMessage(content=self.prompts.ai_message_prefix))

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
            
            # Debug logging to understand the response format
            if self.logger:
                self.logger.debug(f"Raw LLM response for {self.config.name}: {repr(response)}", extra={
                    "component": self.config.name,
                    "data": {"response_type": type(response).__name__, "response_length": len(str(response))}
                })
            
            # Return structured output with optional message capture
            result = {
                "agent_response": response,
                "llm_used": True
            }
            
            # Capture messages if requested
            if include_messages_in_artifacts:
                result["messages"] = [
                    {
                        "type": "system" if isinstance(msg, SystemMessage) else 
                                "human" if isinstance(msg, HumanMessage) else 
                                "ai" if isinstance(msg, AIMessage) else "unknown",
                        "content": msg.content
                    }
                    for msg in messages
                ]
            
            return result
            
        except Exception as e:
            if self.logger:
                log_error(self.logger, f"LangChain execution failed for {self.config.name}: {str(e)}", self.config.name, e)
            # Fallback to basic output if LangChain fails
            return {
                "agent_response": f"Error in {self.config.name}: {str(e)}",
                "llm_used": False,
                "error": str(e)
            }

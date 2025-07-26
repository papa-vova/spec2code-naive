"""
Step 4: Make a plan of implementing the whole set of steps
"""
from typing import List, Dict, Any
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_core.language_models.base import BaseLanguageModel
from exceptions import PlanGenerationError, LLMError


class PlanMakerTool(BaseTool):
    """Tool for creating implementation plans."""
    name: str = "plan_maker"
    description: str = "Creates detailed implementation plans from decomposed steps"
    
    def _run(self, decomposed_steps: str) -> str:
        """Create implementation plan from steps.
        
        Raises:
            PlanGenerationError: If plan generation fails
        """
        try:
            if not decomposed_steps or not decomposed_steps.strip():
                raise PlanGenerationError("Empty or invalid input provided for plan generation")
            
            steps_list = decomposed_steps.split('\n')
            
            plan = f"""
IMPLEMENTATION PLAN
===================

Input Steps: {len(steps_list)} steps received

Planned Implementation Tasks:
1. Setup project structure
2. Implement core functionality for: {decomposed_steps[:100]}...
3. Add error handling and validation
4. Create tests and documentation
5. Integration and deployment

Dependencies: Sequential execution required
Complexity: Medium
Resources: Python, relevant libraries
"""
            return plan.strip()
        except Exception as e:
            if isinstance(e, PlanGenerationError):
                raise
            raise PlanGenerationError(f"Failed to generate implementation plan: {str(e)}")


class PlanMakerAgent:
    """LangChain agent responsible for creating implementation plans from decomposed steps."""
    
    def __init__(self, llm: BaseLanguageModel = None, dry_run: bool = False):
        self.llm = llm
        self.dry_run = dry_run
        self.tool = PlanMakerTool()
        
        # Create prompt template for the agent
        self.prompt = PromptTemplate(
            input_variables=["decomposed_steps"],
            template="""
You are a technical agent. Given the following feature description,
create a detailed implementation plan.

Feature Description:
{decomposed_steps}

Create an implementation plan that includes:
1. Ordered sequence of implementation tasks
2. Dependencies between tasks
3. Estimated complexity for each task
4. Required resources/technologies

Implementation Plan:
"""
        )
    
    def create_plan(self, input_description: str) -> str:
        """
        Takes a description and creates an implementation plan using LangChain agent.
        
        Args:
            input_description: Free text description of what should be done
            
        Returns:
            Implementation plan as string
            
        Raises:
            PlanGenerationError: If plan creation fails
            LLMError: If LLM operations fail
        """
        try:
            if not input_description or not input_description.strip():
                raise PlanGenerationError("Empty or invalid input description provided")
            
            # Use the description directly instead of treating it as a list
            description_text = input_description
            
            if self.dry_run:
                # Use tool-based implementation for dry-run mode
                return self.tool._run(description_text)
            
            if not self.llm:
                raise PlanGenerationError("No LLM configured - agent requires a language model to generate plans")
            
            # Use LangChain LLM to generate plan
            try:
                formatted_prompt = self.prompt.format(decomposed_steps=description_text)
                response = self.llm.invoke(formatted_prompt)
                
                if not response:
                    raise LLMError("LLM returned empty response")
                
                result = response.content if hasattr(response, 'content') else str(response)
                
                if not result or not result.strip():
                    raise LLMError("LLM returned empty or invalid plan")
                
                return result
            except Exception as e:
                if isinstance(e, (PlanGenerationError, LLMError)):
                    raise
                raise LLMError(f"LLM operation failed: {str(e)}")
                
        except (PlanGenerationError, LLMError):
            raise
        except Exception as e:
            raise PlanGenerationError(f"Unexpected error in plan creation: {str(e)}")

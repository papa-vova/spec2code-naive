"""
Step 4: Make a plan of implementing the whole set of steps
"""
from typing import List, Dict, Any
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_core.language_models.base import BaseLanguageModel


class PlanMakerTool(BaseTool):
    """Tool for creating implementation plans."""
    name: str = "plan_maker"
    description: str = "Creates detailed implementation plans from decomposed steps"
    
    def _run(self, decomposed_steps: str) -> str:
        """Create implementation plan from steps."""
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


class PlanMakerAgent:
    """LangChain agent responsible for creating implementation plans from decomposed steps."""
    
    def __init__(self, llm: BaseLanguageModel = None):
        self.llm = llm
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
        """
        # Use the description directly instead of treating it as a list
        description_text = input_description
        
        if self.llm:
            # Use LangChain LLM if available
            formatted_prompt = self.prompt.format(decomposed_steps=description_text)
            response = self.llm.invoke(formatted_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        else:
            # Fallback to tool-based implementation for skeleton
            return self.tool._run(description_text)

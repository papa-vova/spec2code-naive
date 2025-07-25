"""
Step 5: Produce N independent critical reports on the plan's consistency
"""
from typing import List, Dict, Any
from enum import Enum
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain_core.language_models.base import BaseLanguageModel


class ReportType(Enum):
    TECHNICAL_FEASIBILITY = "technical_feasibility"
    RESOURCE_ADEQUACY = "resource_adequacy"
    TIMELINE_REALISM = "timeline_realism"
    DEPENDENCY_ANALYSIS = "dependency_analysis"


class PlanCritiqueTool(BaseTool):
    """Tool for generating plan critique reports."""
    name: str = "plan_critique"
    description: str = "Generates critical analysis reports on implementation plan consistency"
    report_type: ReportType
    
    def __init__(self, report_type: ReportType):
        super().__init__(report_type=report_type)
    
    def _run(self, plan: str) -> Dict[str, Any]:
        """Generate critique report for the given plan."""
        # Mock implementation with different perspectives based on report type
        mock_reports = {
            ReportType.TECHNICAL_FEASIBILITY: {
                "type": "Technical Feasibility",
                "score": 7.5,
                "summary": "Plan is technically sound with moderate complexity",
                "concerns": ["Technology stack needs validation", "Integration complexity"],
                "recommendations": ["Prototype critical components", "Define clear interfaces"]
            },
            ReportType.RESOURCE_ADEQUACY: {
                "type": "Resource Adequacy", 
                "score": 6.0,
                "summary": "Resources appear adequate but tight",
                "concerns": ["Limited expertise in some areas", "Time constraints"],
                "recommendations": ["Add senior developer", "Extend timeline by 20%"]
            },
            ReportType.TIMELINE_REALISM: {
                "type": "Timeline Realism",
                "score": 5.5,
                "summary": "Timeline is optimistic, risks present",
                "concerns": ["Aggressive milestones", "No buffer time"],
                "recommendations": ["Add contingency time", "Parallel task execution"]
            },
            ReportType.DEPENDENCY_ANALYSIS: {
                "type": "Dependency Analysis",
                "score": 8.0,
                "summary": "Dependencies well-identified and manageable",
                "concerns": ["Some circular dependencies possible"],
                "recommendations": ["Create dependency matrix", "Define clear interfaces"]
            }
        }
        return mock_reports.get(self.report_type, {
            "type": "Unknown",
            "score": 5.0,
            "summary": "Analysis pending",
            "concerns": [],
            "recommendations": []
        })


class ReportGeneratorAgent:
    """LangChain agent responsible for generating independent critical reports on plan consistency."""
    
    def __init__(self, report_type: ReportType, llm: BaseLanguageModel = None):
        self.report_type = report_type
        self.llm = llm
        self.tool = PlanCritiqueTool(report_type)
        
        # Create specialized prompt based on report type
        self.prompt = self._create_prompt()
    
    def _create_prompt(self) -> PromptTemplate:
        """Create specialized prompt based on report type."""
        prompts = {
            ReportType.TECHNICAL_FEASIBILITY: """
You are a technical feasibility analyst. Evaluate the following implementation plan
for technical soundness and feasibility.

Implementation Plan:
{plan}

Provide a critical report focusing on:
- Technical complexity assessment
- Technology stack appropriateness
- Potential technical risks
- Implementation challenges

Technical Feasibility Report:
""",
            
            ReportType.RESOURCE_ADEQUACY: """
You are a resource planning analyst. Evaluate the following implementation plan
for resource adequacy and allocation.

Implementation Plan:
{plan}

Provide a critical report focusing on:
- Required skill sets and expertise
- Time and effort estimates
- Resource availability concerns
- Bottleneck identification

Resource Adequacy Report:
""",
            
            ReportType.TIMELINE_REALISM: """
You are a project timeline analyst. Evaluate the following implementation plan
for timeline realism and scheduling.

Implementation Plan:
{plan}

Provide a critical report focusing on:
- Task duration estimates
- Critical path analysis
- Schedule risk factors
- Milestone achievability

Timeline Realism Report:
""",
            
            ReportType.DEPENDENCY_ANALYSIS: """
You are a dependency analysis specialist. Evaluate the following implementation plan
for dependency management and sequencing.

Implementation Plan:
{plan}

Provide a critical report focusing on:
- Task interdependencies
- Blocking relationships
- Parallel execution opportunities
- Dependency risk assessment

Dependency Analysis Report:
"""
        }
        
        return PromptTemplate(
            input_variables=["plan"],
            template=prompts[self.report_type]
        )
    
    def generate_report(self, plan: str) -> Dict[str, Any]:
        """
        Generate an independent critical report on the plan using LangChain agent.
        
        Args:
            plan: Implementation plan to analyze
            
        Returns:
            Dictionary containing report details
        """
        if self.llm:
            # Use LangChain LLM if available
            formatted_prompt = self.prompt.format(plan=plan)
            response = self.llm.invoke(formatted_prompt)
            
            # Parse LLM response into structured format
            # For now, return structured mock data with LLM analysis
            llm_analysis = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "type": self.report_type.value.replace('_', ' ').title(),
                "score": 7.0,  # Could be extracted from LLM response
                "summary": llm_analysis[:100] + "...",
                "concerns": ["LLM-identified concern 1", "LLM-identified concern 2"],
                "recommendations": ["LLM recommendation 1", "LLM recommendation 2"],
                "full_analysis": llm_analysis
            }
        else:
            # Fallback to tool-based implementation for skeleton
            return self.tool._run(plan)


def create_report_generators(n: int = 4) -> List[ReportGeneratorAgent]:
    """
    Create N independent report generator agents.
    
    Args:
        n: Number of report generators to create
        
    Returns:
        List of ReportGeneratorAgent instances
    """
    report_types = list(ReportType)
    generators = []
    
    for i in range(n):
        report_type = report_types[i % len(report_types)]
        generators.append(ReportGeneratorAgent(report_type))
    
    return generators

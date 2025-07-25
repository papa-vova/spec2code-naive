# spec2code-naïve Multi-Agent Langchain Project Plan

## Notes
- The user aims to build a multi-agent application in Python using Langchain.
- The purpose is to generate relevant code snippets for a given feature input, following the sketched flow.
- "Tier-k" labels indicate priority order for implementation.
- All agent logic must be implemented using LangChain agents (not plain Python classes). This is a strict requirement for all future and refactored code.

## Detailed Flow Description

**Planning/Analysis branch**
1. Parse the feature description
2. Refine in your own working and confirm
3. Decompose into actionable deliveries or steps
4. Make a plan of implementing the whole set of steps
5. Produce N independent critical reports on the plan's consistency
6. Do an independent comparison of the reports and generate a metric
7. Decision: "metric ok?"
   - If no → loop back to "Make a plan" step
   - If yes → proceed to implementation

**Implementation branch**
1. Take one step from the plan
2. Implement
3. Build
4. Correct build errors (with loop back to Implement until successful)
5. Produce M independent critical reports on the implementation consistency
6. Do an independent comparison of the reports and generate a metric
7. Decision: "metric ok?"
   - If no → loop back to "Implement" step
   - If yes → check are "all steps done?"
     - If no → loop back to "Take one step from the plan"
     - If yes → "rock'n'roll" (completion)

**Key Components:**
- Both branches generate **multiple independent reports** (N and M respectively)
- **Independent comparison** steps analyze reports and produce metrics
- **Conditional logic** uses metrics to drive iteration control
- Flow continues until metrics are satisfactory and all steps are completed

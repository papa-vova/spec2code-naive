"""
Configuration-driven orchestrator for executing agent pipelines.
Replaces hardcoded pipeline logic with configurable agent sequences.
"""
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from agentic.audits.gates import (
    run_deterministic_audit,
    run_semantic_audit,
    run_sufficiency_evaluation,
)
from agentic.audits.traceability import build_traceability_matrix
from agentic.artifacts.models import (
    Artifact,
    ArtifactIdentity,
    ArtifactProvenance,
    ArtifactType,
    ModelConfigRef,
    PromptRef,
    QualityMetadata,
    compute_content_hash,
)
from agentic.artifacts.store import ArtifactStore
from agentic.collaboration.event_log import CollaborationEventLog
from agentic.collaboration.models import CollaborationEvent, CollaborationEventType
from config_system.config_loader import ConfigLoader
from config_system.agent_factory import AgentFactory
from core.agent import Agent
from exceptions import PipelineError
from logging_config import log_step_start, log_step_complete, log_error


AGENT_ARTIFACT_MAP: Dict[str, ArtifactType] = {
    "product_owner": ArtifactType.PROBLEM_BRIEF,
    "business_analyst": ArtifactType.BUSINESS_REQUIREMENTS,
    "ba_lead": ArtifactType.NON_FUNCTIONAL_REQUIREMENTS,
    "solution_architect": ArtifactType.C4_MODEL,
    "system_analyst": ArtifactType.IMPLEMENTABLE_SPEC,
    "developer": ArtifactType.IMPLEMENTATION_DESIGN,
    "senior_developer": ArtifactType.DESIGN_REVIEW,
    "security_reviewer": ArtifactType.THREAT_MODEL,
    "qa_engineer": ArtifactType.TEST_PLAN,
    "plan_maker": ArtifactType.IMPLEMENTATION_DESIGN,
    "plan_critique_generator": ArtifactType.DESIGN_REVIEW,
    "plan_critique_comparator": ArtifactType.CODE_REVIEW,
}


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
    
    def execute_pipeline(
        self,
        input_data: Dict[str, Any],
        run_id: Optional[str] = None,
        artifact_store: Optional[ArtifactStore] = None,
        collaboration_event_log: Optional[CollaborationEventLog] = None,
    ) -> Dict[str, Any]:
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
        artifacts_manifest: List[Dict[str, Any]] = []
        audit_config = self.config_loader.get_audit_config()
        confidence_threshold = audit_config.min_confidence_to_proceed

        if collaboration_event_log and run_id:
            self._emit_collaboration_event(
                collaboration_event_log=collaboration_event_log,
                run_id=run_id,
                actor="orchestrator",
                event_type=CollaborationEventType.ORCHESTRATOR_DECISION_MADE,
                references=[],
                summary="Pipeline execution started",
            )
        
        try:
            sufficiency_assessment = run_sufficiency_evaluation(
                pipeline_input=input_data,
                min_content_size=audit_config.min_input_size_for_sufficiency,
                insufficient_markers=audit_config.insufficient_markers,
            )
            if artifact_store and run_id:
                sufficiency_artifact = self._build_system_artifact(
                    run_id=run_id,
                    artifact_type=ArtifactType.INFO_SUFFICIENCY_ASSESSMENT,
                    content=sufficiency_assessment.model_dump(mode="json"),
                )
                artifact_path = artifact_store.write_artifact(run_id, sufficiency_artifact)
                if artifact_path:
                    self._append_manifest_entry(
                        artifacts_manifest=artifacts_manifest,
                        run_id=run_id,
                        artifact_store=artifact_store,
                        artifact=sufficiency_artifact,
                        artifact_path=artifact_path,
                    )

            confidence_score = sufficiency_assessment.confidence_score or 0.0
            if confidence_score < confidence_threshold:
                if artifact_store and run_id:
                    artifact_store.write_audit_results(
                        run_id,
                        {
                            "deterministic": {"passed": True, "errors": [], "results": {}},
                            "semantic": {
                                "confidence_score": confidence_score,
                                "blocking_gaps": sufficiency_assessment.blocking_gaps,
                                "evidence_refs": [],
                                "rubric_ref": audit_config.sufficiency_rubric,
                            },
                            "sufficiency": sufficiency_assessment.model_dump(mode="json"),
                            "traceability_matrix_ref": None,
                        },
                    )
                if collaboration_event_log and run_id:
                    self._emit_collaboration_event(
                        collaboration_event_log=collaboration_event_log,
                        run_id=run_id,
                        actor="orchestrator",
                        event_type=CollaborationEventType.AUDIT_GATE_FAILED,
                        references=[ArtifactType.INFO_SUFFICIENCY_ASSESSMENT.value],
                        summary="Sufficiency audit failed",
                    )
                    self._emit_collaboration_event(
                        collaboration_event_log=collaboration_event_log,
                        run_id=run_id,
                        actor="orchestrator",
                        event_type=CollaborationEventType.ORCHESTRATOR_DECISION_MADE,
                        references=[ArtifactType.INFO_SUFFICIENCY_ASSESSMENT.value],
                        summary="Pipeline stopped: insufficient information",
                    )
                return {
                    "pipeline_name": self.pipeline_config.name,
                    "execution_successful": False,
                    "pipeline_input": pipeline_data["pipeline_input"],
                    "agents": {},
                    "metadata": {
                        **pipeline_data["metadata"],
                        "execution_time": (time.time() - pipeline_start_time) * 1000,
                        "blocking_gaps": sufficiency_assessment.blocking_gaps,
                    },
                    "artifacts_manifest": artifacts_manifest,
                }

            if collaboration_event_log and run_id:
                self._emit_collaboration_event(
                    collaboration_event_log=collaboration_event_log,
                    run_id=run_id,
                    actor="orchestrator",
                    event_type=CollaborationEventType.AUDIT_GATE_PASSED,
                    references=[ArtifactType.INFO_SUFFICIENCY_ASSESSMENT.value],
                    summary="Sufficiency audit passed",
                )

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
                role_model_name = self._resolve_role_model(agent_config.name)
                agent = self._create_agent(agent_config.name, role_model_name)
                
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
                        "prompt_templates_used": agent_output.get("prompt_templates_used", []),
                        "input_sources": input_sources,
                        "role_model_profile_id": agent_config.name,
                        "role_model_name": role_model_name,
                    }
                }

                if artifact_store and run_id:
                    artifact = self._build_artifact(
                        run_id=run_id,
                        agent_name=agent_config.name,
                        role_model_name=role_model_name,
                        agent_output=agent_output["output"],
                        prompt_templates_used=agent_output.get("prompt_templates_used", []),
                    )
                    artifact_path = artifact_store.write_artifact(run_id, artifact)
                    if artifact_path:
                        self._append_manifest_entry(
                            artifacts_manifest=artifacts_manifest,
                            run_id=run_id,
                            artifact_store=artifact_store,
                            artifact=artifact,
                            artifact_path=artifact_path,
                        )
                        if collaboration_event_log:
                            self._emit_collaboration_event(
                                collaboration_event_log=collaboration_event_log,
                                run_id=run_id,
                                actor=agent_config.name,
                                event_type=CollaborationEventType.ARTIFACT_PRODUCED,
                                references=[artifact.identity.artifact_id, artifact.content_hash],
                                summary=f"Artifact {artifact.identity.artifact_type.value} produced",
                            )

                if self.logger:
                    log_step_complete(
                        self.logger,
                        "Orchestrator",
                        f"agent_{agent_config.name}",
                        f"Agent {agent_config.name} completed successfully",
                        {
                            "agent_name": agent_config.name,
                            "output_keys": list(agent_output["output"].keys())
                            if isinstance(agent_output["output"], dict)
                            else ["scalar"],
                        },
                        pipeline_data["agents"][agent_config.name]["metadata"]["execution_time"],
                    )

            traceability_matrix_ref: Optional[str] = None
            if artifact_store and run_id:
                traceability_matrix = build_traceability_matrix(artifact_store, run_id)
                traceability_artifact = self._build_system_artifact(
                    run_id=run_id,
                    artifact_type=ArtifactType.TRACEABILITY_MATRIX,
                    content=traceability_matrix.model_dump(mode="json"),
                )
                traceability_path = artifact_store.write_artifact(run_id, traceability_artifact)
                if traceability_path:
                    traceability_matrix_ref = str(
                        traceability_path.relative_to(artifact_store.get_run_directory(run_id))
                    )
                    self._append_manifest_entry(
                        artifacts_manifest=artifacts_manifest,
                        run_id=run_id,
                        artifact_store=artifact_store,
                        artifact=traceability_artifact,
                        artifact_path=traceability_path,
                    )
                    if collaboration_event_log:
                        self._emit_collaboration_event(
                            collaboration_event_log=collaboration_event_log,
                            run_id=run_id,
                            actor="orchestrator",
                            event_type=CollaborationEventType.ARTIFACT_PRODUCED,
                            references=[
                                traceability_artifact.identity.artifact_id,
                                traceability_artifact.content_hash,
                            ],
                            summary=f"Artifact {traceability_artifact.identity.artifact_type.value} produced",
                        )

            audit_results = {"passed": True, "errors": [], "results": {}}
            semantic_results = {
                "confidence_score": 1.0,
                "blocking_gaps": [],
                "evidence_refs": [],
                "rubric_ref": audit_config.sufficiency_rubric,
            }
            if artifact_store and run_id:
                contents = self._collect_artifact_contents(artifact_store, run_id)
                audit_results = run_deterministic_audit(contents)
                semantic_results = run_semantic_audit(contents, audit_config.sufficiency_rubric)

                artifact_store.write_audit_results(
                    run_id,
                    {
                        "deterministic": audit_results,
                        "semantic": semantic_results,
                        "sufficiency": sufficiency_assessment.model_dump(mode="json"),
                        "traceability_matrix_ref": traceability_matrix_ref,
                    },
                )
                if collaboration_event_log:
                    self._emit_collaboration_event(
                        collaboration_event_log=collaboration_event_log,
                        run_id=run_id,
                        actor="orchestrator",
                        event_type=(
                            CollaborationEventType.AUDIT_GATE_PASSED
                            if audit_results.get("passed")
                            else CollaborationEventType.AUDIT_GATE_FAILED
                        ),
                        references=["audits/audit_results.json"],
                        summary=(
                            "Deterministic audit passed"
                            if audit_results.get("passed")
                            else "Deterministic audit failed"
                        ),
                    )
                if not audit_results.get("passed"):
                    raise PipelineError("Deterministic audit failed.")
                semantic_confidence = float(semantic_results.get("confidence_score", 1.0))
                if semantic_confidence < confidence_threshold:
                    if collaboration_event_log:
                        self._emit_collaboration_event(
                            collaboration_event_log=collaboration_event_log,
                            run_id=run_id,
                            actor="orchestrator",
                            event_type=CollaborationEventType.AUDIT_GATE_FAILED,
                            references=["audits/audit_results.json"],
                            summary="Semantic audit confidence below threshold",
                        )
                    raise PipelineError("Semantic audit confidence below threshold.")
                
            # Prepare final result
            total_execution_time = (time.time() - pipeline_start_time) * 1000
            pipeline_data["metadata"]["execution_time"] = total_execution_time
        
            final_result = {
                "pipeline_name": self.pipeline_config.name,
                "execution_successful": True,
                "pipeline_input": pipeline_data["pipeline_input"],
                "agents": pipeline_data["agents"],
                "metadata": pipeline_data["metadata"],
                "artifacts_manifest": artifacts_manifest,
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
            if collaboration_event_log and run_id:
                self._emit_collaboration_event(
                    collaboration_event_log=collaboration_event_log,
                    run_id=run_id,
                    actor="orchestrator",
                    event_type=CollaborationEventType.ORCHESTRATOR_DECISION_MADE,
                    references=[],
                    summary="Pipeline execution completed",
                )
            
            return final_result
            
        except Exception as e:
            if self.logger:
                log_error(self.logger, f"Pipeline execution failed: {str(e)}", "Orchestrator", e)
            raise PipelineError(f"Pipeline execution failed: {str(e)}")

    def _append_manifest_entry(
        self,
        artifacts_manifest: List[Dict[str, Any]],
        run_id: str,
        artifact_store: ArtifactStore,
        artifact: Artifact,
        artifact_path,
    ) -> None:
        """Append one artifact entry to run manifest."""
        artifacts_manifest.append(
            {
                "artifact_type": artifact.identity.artifact_type.value,
                "file": str(artifact_path.relative_to(artifact_store.get_run_directory(run_id))),
                "content_hash": artifact.content_hash,
            }
        )

    def _emit_collaboration_event(
        self,
        collaboration_event_log: CollaborationEventLog,
        run_id: str,
        actor: str,
        event_type: CollaborationEventType,
        references: List[str],
        summary: str,
    ) -> None:
        """Emit one collaboration event and keep orchestration flow resilient."""
        try:
            event = CollaborationEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.now(timezone.utc).isoformat(),
                run_id=run_id,
                actor=actor,
                event_type=event_type,
                references=references,
                summary=summary,
            )
            collaboration_event_log.emit(event)
        except Exception as exc:
            if self.logger:
                self.logger.warning(
                    "Collaboration event emission failed",
                    extra={
                        "component": "Orchestrator",
                        "data": {
                            "event_type": event_type.value,
                            "run_id": run_id,
                            "error_type": type(exc).__name__,
                        },
                    },
                )
    
    def _create_agent(self, agent_name: str, role_model_name: str) -> Agent:
        """Create an agent instance for the given agent name."""
        agent = self.agent_factory.create_agent_with_model(agent_name, role_model_name, self.dry_run)
        if self.logger:
            agent.set_logger(self.logger)
        return agent

    def _collect_artifact_contents(
        self,
        artifact_store: ArtifactStore,
        run_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Load all current artifact contents for audit checks."""
        contents: Dict[str, Dict[str, Any]] = {}
        artifacts_dir = artifact_store.get_run_directory(run_id) / "artifacts"
        for artifact_path in artifacts_dir.glob("*.json"):
            with open(artifact_path, "r", encoding="utf-8") as file_obj:
                payload = json.load(file_obj)
            artifact_type = payload.get("identity", {}).get("artifact_type")
            content = payload.get("content")
            if isinstance(artifact_type, str) and isinstance(content, dict):
                contents[artifact_type] = content
        return contents

    def _resolve_role_model(self, role_name: str) -> str:
        """Resolve role model profile for the configured role."""
        return self.config_loader.get_role_model(role_name)
    
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
        """Execute agent with all templates consolidated into a single execution."""
        # Get available templates from agent's prompts config
        prompts_config = self.config_loader.load_prompts_config(agent_config.name)
        
        # Get include_messages_in_artifacts setting from pipeline config
        include_messages = self.pipeline_config.settings.include_messages_in_artifacts
        
        # Prepare all templates based on the three cases
        all_templates = []
        prompt_templates_used = []
        
        if prompts_config.prompt_templates is None:
            # Case 1: Missing/empty prompt_templates - only human_message_template (no additional templates)
            all_templates = []
            prompt_templates_used = []
        elif isinstance(prompts_config.prompt_templates, str):
            # Case 2: Unnamed template content - add the string content as a template
            all_templates = [prompts_config.prompt_templates]
            prompt_templates_used = ["unnamed_template"]
        elif isinstance(prompts_config.prompt_templates, dict):
            # Case 3: Named templates dictionary - get templates based on pipeline config
            available_templates = list(prompts_config.prompt_templates.keys())
            template_names = agent_config.get_template_names(available_templates)
            
            # Convert template names to actual template content
            all_templates = []
            for template_name in template_names:
                template_content = prompts_config.prompt_templates[template_name]
                all_templates.append(template_content)
            
            prompt_templates_used = template_names
        
        if self.logger:
            log_step_start(
                self.logger,
                agent_config.name,
                "consolidated_execution",
                f"Executing {agent_config.name} with {len(all_templates)} consolidated templates",
                {"template_count": len(all_templates), "prompt_templates_used": prompt_templates_used}
            )
        
        # Execute agent once with all templates consolidated
        result = agent._execute_template(agent_input, all_templates, include_messages)
        
        if self.logger:
            log_step_complete(
                self.logger,
                agent_config.name,
                "consolidated_execution",
                f"Consolidated template execution completed for {agent_config.name}",
                {"template_count": len(all_templates)}
            )
        
        # Return in standard agent output format with template metadata
        return {
            "output": result,
            "metadata": {
                "agent_name": agent_config.name,
                "prompt_templates_used": prompt_templates_used,
                "prompt_templates_count": len(all_templates)
            }
        }

    def _build_artifact(
        self,
        run_id: str,
        agent_name: str,
        role_model_name: str,
        agent_output: Dict[str, Any],
        prompt_templates_used: List[str],
    ) -> Artifact:
        """Build canonical artifact for an agent output."""
        artifact_type = AGENT_ARTIFACT_MAP.get(agent_name, ArtifactType.BUSINESS_REQUIREMENTS)
        model_config = self.config_loader.load_model_config(role_model_name)
        prompt_template_name = prompt_templates_used[0] if prompt_templates_used else "default"
        prompt_template_version = "|".join(prompt_templates_used) if prompt_templates_used else "default"

        quality = QualityMetadata()
        assumptions = agent_output.get("assumptions")
        if isinstance(assumptions, list):
            quality.assumptions = [str(item) for item in assumptions]

        identity = ArtifactIdentity(
            artifact_id=artifact_type.value,
            artifact_type=artifact_type,
            schema_version="1.0.0",
        )
        provenance = ArtifactProvenance(
            run_id=run_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by_role=agent_name,
            created_by_agent_instance_id=str(uuid.uuid4()),
            model_config_ref=ModelConfigRef(
                provider=model_config.provider,
                model_name=model_config.model_name,
                parameters=model_config.parameters,
            ),
            role_model_profile_id=agent_name,
            prompt_ref=PromptRef(
                template_name=prompt_template_name,
                template_version=prompt_template_version,
            ),
        )
        content_hash = compute_content_hash(agent_output)

        return Artifact(
            identity=identity,
            provenance=provenance,
            content=agent_output,
            quality_metadata=quality,
            content_hash=content_hash,
        )

    def _build_system_artifact(
        self,
        run_id: str,
        artifact_type: ArtifactType,
        content: Dict[str, Any],
    ) -> Artifact:
        """Build canonical artifact produced by orchestrator-level system checks."""
        identity = ArtifactIdentity(
            artifact_id=artifact_type.value,
            artifact_type=artifact_type,
            schema_version="1.0.0",
        )
        provenance = ArtifactProvenance(
            run_id=run_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            created_by_role="orchestrator",
            created_by_agent_instance_id=str(uuid.uuid4()),
            model_config_ref=ModelConfigRef(
                provider="system",
                model_name="rule_based",
                parameters={},
            ),
            role_model_profile_id="orchestrator",
            prompt_ref=PromptRef(
                template_name="system",
                template_version="m3",
            ),
        )
        return Artifact(
            identity=identity,
            provenance=provenance,
            content=content,
            quality_metadata=QualityMetadata(),
            content_hash=compute_content_hash(content),
        )

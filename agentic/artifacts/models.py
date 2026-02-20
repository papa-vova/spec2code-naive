"""Canonical artifact models for agentic runs."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """Supported artifact types."""

    PROBLEM_BRIEF = "ProblemBrief"
    BUSINESS_REQUIREMENTS = "BusinessRequirements"
    NON_FUNCTIONAL_REQUIREMENTS = "NonFunctionalRequirements"
    C4_MODEL = "C4Model"
    ARCHITECTURE_DECISION_RECORD_SET = "ArchitectureDecisionRecordSet"
    TECH_STACK_RECOMMENDATION = "TechStackRecommendation"
    ASSUMPTION_LEDGER = "AssumptionLedger"
    TRADEOFF_REGISTER = "TradeoffRegister"
    INFO_SUFFICIENCY_ASSESSMENT = "InfoSufficiencyAssessment"
    TRACEABILITY_MATRIX = "TraceabilityMatrix"
    IMPLEMENTABLE_SPEC = "ImplementableSpec"
    IMPLEMENTATION_DESIGN = "ImplementationDesign"
    WORK_BREAKDOWN = "WorkBreakdown"
    DESIGN_REVIEW = "DesignReview"
    CODE_REVIEW = "CodeReview"
    THREAT_MODEL = "ThreatModel"
    PRIVACY_CHECKLIST = "PrivacyChecklist"
    TEST_PLAN = "TestPlan"
    ACCEPTANCE_TESTS = "AcceptanceTests"
    AMENDMENT = "Amendment"


class ArtifactInputRef(BaseModel):
    """Input reference for artifact provenance."""

    artifact_id: str
    content_hash: str


class ModelConfigRef(BaseModel):
    """Model configuration reference captured in provenance."""

    provider: str
    model_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PromptRef(BaseModel):
    """Prompt template reference captured in provenance."""

    template_name: str
    template_version: str


class ArtifactIdentity(BaseModel):
    """Artifact identity envelope."""

    artifact_id: str
    artifact_type: ArtifactType
    schema_version: str


class ArtifactProvenance(BaseModel):
    """Artifact provenance envelope."""

    run_id: str
    base_run_id: Optional[str] = None
    created_at: str
    created_by_role: str
    created_by_agent_instance_id: str
    inputs: List[ArtifactInputRef] = Field(default_factory=list)
    model_config_ref: ModelConfigRef
    role_model_profile_id: str
    prompt_ref: PromptRef


class QualityMetadata(BaseModel):
    """Shared quality metadata envelope."""

    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)


class Artifact(BaseModel):
    """Canonical artifact envelope."""

    identity: ArtifactIdentity
    provenance: ArtifactProvenance
    content: Dict[str, Any]
    quality_metadata: QualityMetadata = Field(default_factory=QualityMetadata)
    content_hash: str


class ArtifactContentBase(BaseModel):
    """Base type for per-artifact content models."""

    raw_response: Optional[str] = None


class ProblemBriefContent(ArtifactContentBase):
    title: Optional[str] = None
    goals: List[Dict[str, Any]] = Field(default_factory=list)


class BusinessRequirementsContent(ArtifactContentBase):
    title: Optional[str] = None
    functional_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    non_functional_requirements: List[Dict[str, Any]] = Field(default_factory=list)
    resources: Dict[str, Any] = Field(default_factory=dict)


class NonFunctionalRequirementsContent(ArtifactContentBase):
    categories: List[Dict[str, Any]] = Field(default_factory=list)


class C4ModelContent(ArtifactContentBase):
    plantuml_source: Optional[str] = None
    diagrams: List[Dict[str, Any]] = Field(default_factory=list)


class ArchitectureDecisionRecordSetContent(ArtifactContentBase):
    decisions: List[Dict[str, Any]] = Field(default_factory=list)


class TechStackRecommendationContent(ArtifactContentBase):
    stack: List[Dict[str, Any]] = Field(default_factory=list)


class AssumptionLedgerContent(ArtifactContentBase):
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)


class TradeoffRegisterContent(ArtifactContentBase):
    tradeoffs: List[Dict[str, Any]] = Field(default_factory=list)


class AmendmentContent(ArtifactContentBase):
    """Amendment artifact: references base run and amended assumptions/tradeoffs."""

    base_run_id: str
    amended_assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    amended_tradeoffs: List[Dict[str, Any]] = Field(default_factory=list)
    reason: Optional[str] = None


class InfoSufficiencyAssessmentContent(ArtifactContentBase):
    confidence_score: Optional[float] = None
    blocking_gaps: List[Dict[str, Any]] = Field(default_factory=list)


class TraceabilityMatrixContent(ArtifactContentBase):
    rows: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    cells: Dict[str, List[str]] = Field(default_factory=dict)
    gaps: List[Dict[str, Any]] = Field(default_factory=list)


class ImplementableSpecContent(ArtifactContentBase):
    requirements: List[Dict[str, Any]] = Field(default_factory=list)


class ImplementationDesignContent(ArtifactContentBase):
    modules: List[Dict[str, Any]] = Field(default_factory=list)
    algorithms: List[Dict[str, Any]] = Field(default_factory=list)


class WorkBreakdownContent(ArtifactContentBase):
    tasks: List[Dict[str, Any]] = Field(default_factory=list)


class DesignReviewContent(ArtifactContentBase):
    findings: List[Dict[str, Any]] = Field(default_factory=list)


class CodeReviewContent(ArtifactContentBase):
    findings: List[Dict[str, Any]] = Field(default_factory=list)


class ThreatModelContent(ArtifactContentBase):
    threats: List[Dict[str, Any]] = Field(default_factory=list)


class PrivacyChecklistContent(ArtifactContentBase):
    checks: List[Dict[str, Any]] = Field(default_factory=list)


class TestPlanContent(ArtifactContentBase):
    test_suites: List[Dict[str, Any]] = Field(default_factory=list)


class AcceptanceTestsContent(ArtifactContentBase):
    tests: List[Dict[str, Any]] = Field(default_factory=list)


def compute_content_hash(content: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash for artifact content."""
    canonical = json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


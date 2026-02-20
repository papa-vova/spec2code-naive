"""Artifact content model registry."""

from __future__ import annotations

from typing import Dict, Type

from pydantic import BaseModel

from agentic.artifacts.models import (
    AcceptanceTestsContent,
    ArchitectureDecisionRecordSetContent,
    ArtifactType,
    AssumptionLedgerContent,
    BusinessRequirementsContent,
    C4ModelContent,
    CodeReviewContent,
    DesignReviewContent,
    ImplementableSpecContent,
    ImplementationDesignContent,
    InfoSufficiencyAssessmentContent,
    NonFunctionalRequirementsContent,
    PrivacyChecklistContent,
    ProblemBriefContent,
    TraceabilityMatrixContent,
    TechStackRecommendationContent,
    TestPlanContent,
    ThreatModelContent,
    TradeoffRegisterContent,
    WorkBreakdownContent,
)


ARTIFACT_CONTENT_MODELS: Dict[ArtifactType, Type[BaseModel]] = {
    ArtifactType.PROBLEM_BRIEF: ProblemBriefContent,
    ArtifactType.BUSINESS_REQUIREMENTS: BusinessRequirementsContent,
    ArtifactType.NON_FUNCTIONAL_REQUIREMENTS: NonFunctionalRequirementsContent,
    ArtifactType.C4_MODEL: C4ModelContent,
    ArtifactType.ARCHITECTURE_DECISION_RECORD_SET: ArchitectureDecisionRecordSetContent,
    ArtifactType.TECH_STACK_RECOMMENDATION: TechStackRecommendationContent,
    ArtifactType.ASSUMPTION_LEDGER: AssumptionLedgerContent,
    ArtifactType.TRADEOFF_REGISTER: TradeoffRegisterContent,
    ArtifactType.INFO_SUFFICIENCY_ASSESSMENT: InfoSufficiencyAssessmentContent,
    ArtifactType.TRACEABILITY_MATRIX: TraceabilityMatrixContent,
    ArtifactType.IMPLEMENTABLE_SPEC: ImplementableSpecContent,
    ArtifactType.IMPLEMENTATION_DESIGN: ImplementationDesignContent,
    ArtifactType.WORK_BREAKDOWN: WorkBreakdownContent,
    ArtifactType.DESIGN_REVIEW: DesignReviewContent,
    ArtifactType.CODE_REVIEW: CodeReviewContent,
    ArtifactType.THREAT_MODEL: ThreatModelContent,
    ArtifactType.PRIVACY_CHECKLIST: PrivacyChecklistContent,
    ArtifactType.TEST_PLAN: TestPlanContent,
    ArtifactType.ACCEPTANCE_TESTS: AcceptanceTestsContent,
}


def get_content_model(artifact_type: ArtifactType) -> Type[BaseModel]:
    """Resolve content model class for artifact type."""
    return ARTIFACT_CONTENT_MODELS[artifact_type]


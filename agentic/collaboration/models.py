"""Collaboration event models for run-scoped business artifacts."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class CollaborationEventType(str, Enum):
    """Supported collaboration event types."""

    STAKEHOLDER_QUESTION_ASKED = "stakeholder_question_asked"
    STAKEHOLDER_ANSWER_RECEIVED = "stakeholder_answer_received"
    ARTIFACT_PRODUCED = "artifact_produced"
    ARTIFACT_REVISED = "artifact_revised"
    AUDIT_GATE_PASSED = "audit_gate_passed"
    AUDIT_GATE_FAILED = "audit_gate_failed"
    ORCHESTRATOR_DECISION_MADE = "orchestrator_decision_made"


class ContentRef(BaseModel):
    """Reference to a stored collaboration content blob."""

    path: str
    content_hash: str


class CollaborationEvent(BaseModel):
    """Append-only collaboration event entry."""

    event_id: str
    timestamp: str
    run_id: str
    actor: str
    event_type: CollaborationEventType
    references: List[str] = Field(default_factory=list)
    content_ref: Optional[ContentRef] = None
    summary: str


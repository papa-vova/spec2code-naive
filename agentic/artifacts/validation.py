"""Artifact validation helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import ValidationError

from agentic.artifacts.models import Artifact, ArtifactType
from agentic.artifacts.registry import get_content_model


def validate_envelope(artifact_dict: Dict[str, Any]) -> List[str]:
    """Validate artifact envelope and return list of errors."""
    try:
        Artifact.model_validate(artifact_dict)
        return []
    except ValidationError as exc:
        return [err["msg"] for err in exc.errors()]


def validate_content(artifact_type: ArtifactType, content_dict: Dict[str, Any]) -> List[str]:
    """Validate type-specific content and return list of errors."""
    model_cls = get_content_model(artifact_type)
    try:
        model_cls.model_validate(content_dict)
        return []
    except ValidationError as exc:
        return [err["msg"] for err in exc.errors()]


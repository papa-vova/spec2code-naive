#!/usr/bin/env python3
"""Export JSON schemas for canonical artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentic.artifacts.models import Artifact
from agentic.artifacts.registry import ARTIFACT_CONTENT_MODELS


def main() -> int:
    target_dir = Path("agentic/artifacts/schemas")
    target_dir.mkdir(parents=True, exist_ok=True)

    envelope_schema_path = target_dir / "Artifact.schema.json"
    with open(envelope_schema_path, "w", encoding="utf-8") as file_obj:
        json.dump(Artifact.model_json_schema(), file_obj, indent=2, ensure_ascii=False)

    for artifact_type, model_cls in ARTIFACT_CONTENT_MODELS.items():
        schema_path = target_dir / f"{artifact_type.value}.schema.json"
        with open(schema_path, "w", encoding="utf-8") as file_obj:
            json.dump(model_cls.model_json_schema(), file_obj, indent=2, ensure_ascii=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


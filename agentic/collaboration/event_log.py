"""Append-only collaboration event log utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from agentic.collaboration.models import CollaborationEvent, CollaborationEventType


class CollaborationEventLog:
    """Read/write JSONL collaboration events within a run."""

    def __init__(self, collaboration_dir: Path):
        self.collaboration_dir = collaboration_dir
        self.events_file = self.collaboration_dir / "collaboration_events.jsonl"

    def emit(self, event: CollaborationEvent) -> None:
        """Append one event to the run collaboration event log."""
        self.collaboration_dir.mkdir(parents=True, exist_ok=True)
        with open(self.events_file, "a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False))
            file_obj.write("\n")
            file_obj.flush()

    def read_all(self) -> List[CollaborationEvent]:
        """Read and parse all events in insertion order."""
        if not self.events_file.exists():
            return []

        events: List[CollaborationEvent] = []
        with open(self.events_file, "r", encoding="utf-8") as file_obj:
            for line in file_obj:
                payload = line.strip()
                if not payload:
                    continue
                events.append(CollaborationEvent.model_validate_json(payload))
        return events

    def read_by_type(self, event_type: CollaborationEventType) -> List[CollaborationEvent]:
        """Return events matching the given type."""
        return [event for event in self.read_all() if event.event_type == event_type]

    def count(self) -> int:
        """Return total number of collaboration events."""
        return len(self.read_all())


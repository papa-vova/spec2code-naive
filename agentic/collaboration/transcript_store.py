"""Stakeholder transcript and collaboration content storage."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple


def hash_text(text: str) -> str:
    """Compute deterministic SHA-256 hash for plain text content."""
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


class TranscriptStore:
    """Stores stakeholder transcript and content blobs in collaboration folder."""

    def __init__(self, collaboration_dir: Path):
        self.collaboration_dir = collaboration_dir
        self.transcript_file = self.collaboration_dir / "stakeholder_transcript.txt"

    def write_entry(self, role: str, content: str) -> Tuple[str, str]:
        """Append one timestamped transcript entry and return path/hash."""
        self.collaboration_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = f"[{timestamp}] {role}: {content}\n"
        with open(self.transcript_file, "a", encoding="utf-8") as file_obj:
            file_obj.write(entry)
            file_obj.flush()
        return self.transcript_file.name, hash_text(entry)

    def write_content_file(self, filename: str, content: str) -> Tuple[str, str]:
        """Persist one standalone collaboration content file and return path/hash."""
        self.collaboration_dir.mkdir(parents=True, exist_ok=True)
        content_path = self.collaboration_dir / filename
        with open(content_path, "w", encoding="utf-8") as file_obj:
            file_obj.write(content)
            file_obj.flush()
        return content_path.name, hash_text(content)

    def read_transcript(self) -> str:
        """Read full stakeholder transcript content."""
        if not self.transcript_file.exists():
            return ""
        return self.transcript_file.read_text(encoding="utf-8")


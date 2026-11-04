"""Finding records. No auto-fix payload is produced."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Finding:
    rule_id: str
    severity: str
    url: str
    evidence: str
    target: str = ""
    action: str = "report_only"
    file: str = ""
    allowlist: bool = False
    recurrence: int = 0
    repeat: bool = False
    shared_file: str | None = None
    shared_count: int = 0
    shared_urls: list = field(default_factory=list)
    found_at: str = ""
    id: str = ""

    def ensure_id(self) -> None:
        if not self.id:
            raw = f"{self.rule_id}|{self.url}|{self.target}".encode("utf-8")
            self.id = hashlib.sha1(raw).hexdigest()

    def to_json(self) -> dict:
        self.ensure_id()
        return {
            "id": self.id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "url": self.url,
            "evidence": self.evidence,
            "found_at": self.found_at,
            "recurrence": self.recurrence,
            "repeat": self.repeat,
            "shared_file": self.shared_file,
            "shared_count": self.shared_count,
            "shared_urls": list(self.shared_urls),
            "allowlist": self.allowlist,
            "action": self.action,
            "target": self.target,
            "file": self.file,
        }

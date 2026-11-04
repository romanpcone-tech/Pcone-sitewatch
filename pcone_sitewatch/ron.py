"""Ron's published.txt and closed.txt. GET only, 404 is empty."""

from __future__ import annotations

import re
from datetime import datetime

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_published(text: str | None) -> datetime | None:
    if not text:
        return None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            stamp = datetime.fromisoformat(line)
        except ValueError:
            return None
        if stamp.tzinfo is None:
            return None
        return stamp
    return None


def published_line(text: str | None) -> str:
    if not text:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def is_newer(new_text: str | None, saved: str | None) -> bool:
    new_dt = parse_published(new_text)
    if new_dt is None:
        return False
    if not saved:
        return True
    old_dt = parse_published(saved)
    if old_dt is None:
        return True
    return new_dt > old_dt


def parse_closed(text: str | None) -> list[tuple[str, str]]:
    rows = []
    if not text:
        return rows
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()
        parts = line.split()
        if len(parts) < 2 or not _DATE.fullmatch(parts[1]):
            continue
        rows.append((parts[0], parts[1]))
    return rows

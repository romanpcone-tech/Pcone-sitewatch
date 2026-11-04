"""allowlist.txt: rule_id | url | reason | who, date. Globs are ignored."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from pcone_sitewatch.htmlutil import norm_url

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass
class Allow:
    rule_id: str
    url: str
    reason: str
    who: str
    day: date | None


def parse_text(text: str) -> tuple[list[Allow], list[str]]:
    """Return valid rows and ignored notes (globs, empty reason)."""
    rows: list[Allow] = []
    ignored: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 4:
            ignored.append(line)
            continue
        rule_id, url, reason, who = parts[0], parts[1], parts[2], parts[3]
        if "*" in rule_id or "*" in url:
            ignored.append(line)
            continue
        if not reason:
            ignored.append(line)
            continue
        found = _DATE.search(who)
        day = datetime.strptime(found.group(0), "%Y-%m-%d").date() if found else None
        rows.append(Allow(rule_id, url, reason, who, day))
    return rows, ignored


def load(path: str | Path | None) -> tuple[list[Allow], list[str]]:
    if not path:
        return [], []
    file = Path(path)
    if not file.is_file():
        return [], []
    return parse_text(file.read_text(encoding="utf-8"))


def match(rows: list[Allow], rule_id: str, url: str) -> Allow | None:
    target = norm_url(url)
    for row in rows:
        if row.rule_id != rule_id:
            continue
        if norm_url(row.url) == target:
            return row
    return None


def stale(rows: list[Allow], today: date, days: int = 60) -> list[Allow]:
    old = []
    for row in rows:
        if row.day is None:
            continue
        if (today - row.day).days > days:
            old.append(row)
    return old


def report_only_prefixes(canon: dict) -> list[str]:
    """Canon rows that use rule '*' cannot be allowlist.txt lines.

    They are applied as path prefixes: findings become info / report_only.
    """
    prefixes = []
    for row in canon.get("allowlist_seed") or []:
        if row.get("mode") != "report_only" and row.get("rule_hint") != "*":
            continue
        url = str(row.get("url") or "")
        token = url.split("*", 1)[0].strip().split()[0] if url else ""
        if token.startswith("/"):
            prefixes.append(token.rstrip("/"))
    return prefixes


def allowed_anchor_texts(canon: dict) -> list[str]:
    texts = []
    for row in canon.get("allowlist_seed") or []:
        url = str(row.get("url") or "")
        if "«" in url and "»" in url:
            texts.append(url.split("«", 1)[1].split("»", 1)[0])
    return texts


def is_report_only_url(url: str, canon: dict) -> bool:
    path = "/" + url.split("://", 1)[-1].split("/", 1)[-1] if "://" in url else url
    if not path.startswith("/"):
        path = "/" + path
    for prefix in report_only_prefixes(canon):
        if prefix and (prefix in path or path.endswith(prefix + ".html") or path.endswith(prefix)):
            return True
    return False

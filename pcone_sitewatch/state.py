"""Run history. A failed run must not replace this file."""

from __future__ import annotations

import json
from pathlib import Path

from pcone_sitewatch.finding import Finding


def empty() -> dict:
    return {
        "last_run": "",
        "urls_checked": 0,
        "published_at": "",
        "status": "ok",
        "fail_reason": "",
        "new_count": 0,
        "critical_count": 0,
        "hint": "",
        "geometry": "",
        "repo": "https://github.com/romanpcone-tech/Pcone-sitewatch",
        "items": {},
    }


def load(path: Path) -> dict:
    if not path.is_file():
        return empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return empty()
    base = empty()
    base.update(data)
    base["items"] = data.get("items") or {}
    return base


def save(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def merge(state: dict, findings: list[Finding], now: str, closed_rows: list[tuple[str, str]]) -> list[Finding]:
    closed = {item_id: day for item_id, day in closed_rows}
    seen = set()
    for finding in findings:
        if finding.action == "skipped":
            continue
        finding.ensure_id()
        seen.add(finding.id)
        prev = state["items"].get(finding.id)
        if prev is None or not prev.get("first_seen"):
            state["items"][finding.id] = {
                "rule_id": finding.rule_id,
                "url": finding.url,
                "first_seen": now,
                "last_seen": now,
                "fixed_at": None,
                "recurrence": 0,
                "status": "allowed" if finding.allowlist else "open",
                "evidence": finding.evidence,
                "severity": finding.severity,
                "closed_by": None,
                "closed_at": None,
                "times_seen": 1,
            }
            finding.recurrence = 0
            finding.repeat = False
        else:
            times = int(prev.get("times_seen") or 0) + 1
            recurrence = int(prev.get("recurrence") or 0)
            if prev.get("status") == "fixed":
                recurrence += 1
            prev.update(
                {
                    "last_seen": now,
                    "status": "allowed" if finding.allowlist else "open",
                    "fixed_at": None,
                    "recurrence": recurrence,
                    "times_seen": times,
                    "evidence": finding.evidence,
                    "severity": finding.severity,
                }
            )
            state["items"][finding.id] = prev
            finding.recurrence = recurrence
            finding.repeat = recurrence >= 2
        if finding.id in closed:
            state["items"][finding.id]["closed_by"] = "ron"
            state["items"][finding.id]["closed_at"] = closed[finding.id]
    for item_id, prev in list(state["items"].items()):
        if item_id in seen or prev.get("status") not in {"open", "allowed"}:
            continue
        prev["status"] = "fixed"
        prev["fixed_at"] = now
        if item_id in closed:
            prev["closed_by"] = "ron"
            prev["closed_at"] = closed[item_id]
    for item_id, day in closed.items():
        if item_id in state["items"]:
            state["items"][item_id]["closed_by"] = "ron"
            state["items"][item_id]["closed_at"] = day
    return findings


def counts(findings: list[Finding]) -> dict:
    real = [item for item in findings if item.action != "skipped" and not item.allowlist]
    new = 0
    confirmed = 0
    critical = 0
    hint = ""
    for item in real:
        item.ensure_id()
        # times_seen is on state; use recurrence 0 and we pass times via attribute
        times = getattr(item, "times_seen", 1)
        if times <= 1 and item.recurrence == 0:
            new += 1
        else:
            confirmed += 1
        if item.severity == "critical":
            critical += 1
            if not hint:
                hint = item.file or item.url
    return {"new": new, "confirmed": confirmed, "critical": critical, "hint": hint}

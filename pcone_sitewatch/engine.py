"""Run markup rules over a local tree and write the sitewatch/ outputs."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pcone_sitewatch.allowlist import is_report_only_url, load as load_allow, match, stale
from pcone_sitewatch.canon import load as load_canon
from pcone_sitewatch.canon import sha256 as canon_sha
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import load_tree
from pcone_sitewatch.report import digest_line, render, sunday
from pcone_sitewatch.rules import check_page
from pcone_sitewatch.rules.page_4xx import from_sitemap
from pcone_sitewatch import state as state_mod

TZ = ZoneInfo("Asia/Jerusalem")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def israel_now() -> datetime:
    return datetime.now(TZ)


def annotate(findings: list[Finding], pages, canon: dict, allow_rows) -> list[Finding]:
    by_url = {page.url: page for page in pages}
    groups: dict[tuple, list[Finding]] = {}
    for finding in findings:
        if is_report_only_url(finding.url, canon):
            finding.severity = "info"
            finding.action = "report_only"
        row = match(allow_rows, finding.rule_id, finding.url)
        if row is not None:
            finding.allowlist = True
        key = (finding.rule_id, finding.evidence)
        groups.setdefault(key, []).append(finding)
    for items in groups.values():
        urls = {item.url for item in items}
        if len(urls) < 3:
            continue
        asset_sets = []
        for url in urls:
            page = by_url.get(url)
            if page is None:
                continue
            refs = set()
            for asset in page.parsed()["assets"]:
                path = asset["url"].split("?", 1)[0]
                if path.endswith((".css", ".js", ".mjs")):
                    refs.add(path)
            asset_sets.append(refs)
        shared = set.intersection(*asset_sets) if asset_sets else set()
        shared_file = sorted(shared)[0] if len(shared) == 1 else None
        for item in items:
            item.shared_count = len(urls)
            item.shared_file = shared_file
            item.shared_urls = sorted(urls)
    return findings


def scan(root: Path, base: str, canon: dict, allow_rows) -> tuple[list[Finding], int]:
    pages = load_tree(root, base)
    found: list[Finding] = []
    for page in pages:
        found.extend(check_page(page, canon))
    found.extend(from_sitemap(root, base, canon))
    annotate(found, pages, canon, allow_rows)
    return found, len(pages)


def write_outputs(out: Path, findings: list[Finding], urls: int, canon_path: Path, mode: str, state: dict, allow_rows, when: datetime) -> None:
    out.mkdir(parents=True, exist_ok=True)
    stamp = when.isoformat(timespec="seconds")
    for item in findings:
        if not item.found_at:
            item.found_at = stamp
        item.ensure_id()
    lines = [json.dumps(item.to_json(), ensure_ascii=False) for item in findings]
    text = ("\n".join(lines) + "\n") if lines else ""
    (out / "findings.jsonl").write_text(text, encoding="utf-8")
    history = out / "history"
    history.mkdir(exist_ok=True)
    stamp = when.strftime("%Y-%m-%d-%H%M")
    (history / f"{stamp}.jsonl").write_text(text, encoding="utf-8")
    _prune_history(history, when.date())
    show_stale = sunday(when.date())
    stale_rows = stale(allow_rows, when.date()) if show_stale else []
    (out / "report.html").write_text(
        render(findings, urls, stale_rows, show_stale),
        encoding="utf-8",
    )
    critical = [item for item in findings if item.severity == "critical" and not item.allowlist and item.action != "skipped"]
    alert = out / "ALERT.md"
    if critical:
        body = ["# ALERT", ""]
        for item in critical:
            body.append(f"- {item.rule_id} {item.url} — {item.evidence.splitlines()[0][:180]}")
        alert.write_text("\n".join(body) + "\n", encoding="utf-8")
    elif alert.is_file() and mode != "mark-failed":
        alert.unlink()
    real = [item for item in findings if not item.allowlist and item.action != "skipped"]
    new = sum(1 for item in real if item.recurrence == 0 and getattr(item, "times_seen", 1) <= 1)
    confirmed = sum(1 for item in real if not (item.recurrence == 0 and getattr(item, "times_seen", 1) <= 1))
    state["urls_checked"] = urls
    state["new_count"] = new
    state["critical_count"] = len(critical)
    state["hint"] = critical[0].file if critical else (real[0].file if real else "")
    state["status"] = "ok"
    state["last_run"] = when.isoformat(timespec="seconds")
    if mode == "nightly":
        state["last_nightly"] = state["last_run"]
    summary = digest_line(state)
    if show_stale and stale_rows:
        summary = summary[:140]
        (out / "SUMMARY.txt").write_text(summary + "\nпроверить, ещё задумано?\n", encoding="utf-8")
    else:
        (out / "SUMMARY.txt").write_text(summary + "\n", encoding="utf-8")
    meta = {
        "schema_version": 1,
        "mode": mode,
        "started_at": state.get("started_at") or state["last_run"],
        "ended_at": state["last_run"],
        "urls_checked": urls,
        "canon_sha256": canon_sha(canon_path) if canon_path else "",
        "status": "ok",
        "last_run_utc": datetime.now(tz=TZ).astimezone(tz=__import__("datetime").timezone.utc).isoformat(timespec="seconds"),
        "last_nightly_utc": state.get("last_nightly_utc") or "",
        "geometry": state.get("geometry") or "",
        "rules_version": "v2",
    }
    if mode == "nightly":
        meta["last_nightly_utc"] = meta["last_run_utc"]
        state["last_nightly_utc"] = meta["last_run_utc"]
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    state_mod.save(out / "state.json", state)


def _prune_history(history: Path, today) -> None:
    from datetime import timedelta

    cutoff = today - timedelta(days=30)
    for path in history.glob("*.jsonl"):
        name = path.name[:10]
        try:
            day = datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            path.unlink()


def commit_subject(when: datetime, new: int, confirmed: int, fixed: int, critical: int) -> str:
    return (
        f"sitewatch: {when.strftime('%d.%m')} {when.strftime('%H:%M')} — "
        f"{new} новых, {confirmed} подтверждённых, {fixed} исправлено, {critical} критичных"
    )


def fail(out: Path, reason: str) -> None:
    """Write the emergency files and leave findings/state untouched."""
    out.mkdir(parents=True, exist_ok=True)
    (out / "ALERT.md").write_text(f"прогон не прошёл: {reason}\n", encoding="utf-8")
    (out / "SUMMARY.txt").write_text(f"Сторож: прогон не прошёл — {reason}\n"[:141], encoding="utf-8")

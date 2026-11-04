"""CLI: fast, nightly, preflight, verify, watch-silence, digest."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from pcone_sitewatch.allowlist import load as load_allow
from pcone_sitewatch.canon import CanonError, default_path, load as load_canon
from pcone_sitewatch.engine import TZ, annotate, commit_subject, fail, israel_now, now_iso, scan, write_outputs
from pcone_sitewatch.geometry import check as geometry_check
from pcone_sitewatch.htmlutil import load_tree
from pcone_sitewatch.live import stage
from pcone_sitewatch.net import Client
from pcone_sitewatch.report import digest_line
from pcone_sitewatch.ron import is_newer, parse_closed, published_line
from pcone_sitewatch.rules import check_page
from pcone_sitewatch import state as state_mod

CLOSED_URL = "https://ron.pcone.co.il/files/sitewatch/closed.txt"
PUBLISHED_URL = "https://ron.pcone.co.il/files/sitewatch/published.txt"
BASE = "https://pconelab.co.il"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pcone-sitewatch")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add_common(command):
        command.add_argument("--root", default="")
        command.add_argument("--base", default=BASE)
        command.add_argument("--out", default="sitewatch")
        command.add_argument("--canon", default="")
        command.add_argument("--allow", default="sitewatch/allowlist.txt")
        command.add_argument("--offline", action="store_true")

    pre = sub.add_parser("preflight")
    add_common(pre)
    fast = sub.add_parser("fast")
    add_common(fast)
    fast.add_argument("--publish-gate", action="store_true")
    nightly = sub.add_parser("nightly")
    add_common(nightly)
    verify = sub.add_parser("verify")
    verify.add_argument("--root", required=True)
    verify.add_argument("--before", required=True)
    verify.add_argument("--pages", required=True)
    verify.add_argument("--base", default=BASE)
    verify.add_argument("--canon", default="")
    silence = sub.add_parser("watch-silence")
    silence.add_argument("--state", required=True)
    silence.add_argument("--max-age", default="26h")
    digest = sub.add_parser("digest")
    digest.add_argument("--state", required=True)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "digest":
            return cmd_digest(args)
        if args.cmd == "watch-silence":
            return cmd_silence(args)
        if args.cmd == "verify":
            return cmd_verify(args)
        return cmd_scan(args)
    except CanonError as exc:
        out = Path(getattr(args, "out", "sitewatch"))
        fail(out, str(exc))
        print(f"прогон не прошёл: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        out = Path(getattr(args, "out", "sitewatch"))
        fail(out, str(exc))
        print(f"прогон не прошёл: {exc}", file=sys.stderr)
        return 1


def _canon(args):
    return load_canon(args.canon or None), Path(args.canon) if args.canon else default_path()


def cmd_digest(args) -> int:
    state = state_mod.load(Path(args.state))
    print(digest_line(state))
    return 0


def _age(value: str) -> timedelta:
    text = value.strip().lower()
    if text.endswith("h"):
        return timedelta(hours=float(text[:-1]))
    return timedelta(hours=float(text))


def cmd_silence(args) -> int:
    path = Path(args.state)
    state = state_mod.load(path)
    last = state.get("last_run") or ""
    limit = _age(args.max_age)
    stale = True
    when = ""
    if last:
        try:
            stamp = datetime.fromisoformat(last)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=TZ)
            stale = datetime.now(TZ) - stamp > limit
            when = stamp.isoformat(timespec="seconds")
        except ValueError:
            stale = True
            when = last
    if not stale:
        return 0
    shown = when or "нет"
    line = f"сторож молчит: последний прогон {shown}"
    print(line)
    folder = path.parent
    (folder / "ALERT.md").write_text(line + "\n", encoding="utf-8")
    (folder / "SUMMARY.txt").write_text(line + "\n", encoding="utf-8")
    return 1


def _page_list(raw: str) -> list[str]:
    file = Path(raw)
    if file.is_file():
        text = file.read_text(encoding="utf-8")
        return [line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")]
    return [part.strip() for part in raw.split(",") if part.strip()]


def cmd_verify(args) -> int:
    canon, _path = _canon(args)
    root = Path(args.root)
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    previous = before.get("findings") or []
    wanted = set(_page_list(args.pages))
    pages = []
    for page in load_tree(root, args.base):
        if page.url in wanted or page.rel in wanted or Path(page.rel).name in wanted:
            pages.append(page)
    found = []
    for page in pages:
        found.extend(check_page(page, canon))
    prev_keys = {(item.get("rule_id"), item.get("url")) for item in previous}
    prev_count = len(previous)
    new_high = [
        item
        for item in found
        if item.severity in {"critical", "high"} and (item.rule_id, item.url) not in prev_keys
    ]
    worse = bool(new_high) or len(found) > prev_count
    if not worse:
        return 0
    reason = "new critical/high" if new_high else f"findings {prev_count} -> {len(found)}"
    files = sorted({item.file or item.url for item in (new_high or found)})
    for name in files or ["?"]:
        print(f"reverted: {name} {reason}")
    return 2


def _fetch_text(url: str) -> tuple[int, str]:
    return Client().get_text(url, timeout=15)


def cmd_scan(args) -> int:
    canon, canon_path = _canon(args)
    out = Path(args.out)
    allow_rows, _ignored = load_allow(args.allow)
    if args.cmd == "fast" and args.publish_gate:
        status, text = (0, "") if args.offline else _fetch_text(PUBLISHED_URL)
        if status == 404 or not published_line(text):
            print("SITEWATCH_NOCOMMIT")
            return 0
        state = state_mod.load(out / "state.json")
        if not is_newer(text, state.get("published_at")):
            print("SITEWATCH_NOCOMMIT")
            return 0
        state["published_at"] = published_line(text)
        state_mod.save(out / "state.json", state)
    root = Path(args.root) if args.root else None
    when = israel_now()
    state = state_mod.load(out / "state.json")
    state["started_at"] = now_iso()
    closed_rows: list[tuple[str, str]] = []
    if args.cmd != "preflight" and not args.offline:
        status, text = _fetch_text(CLOSED_URL)
        if status == 200:
            closed_rows = parse_closed(text)
    if root is None:
        if args.cmd == "preflight":
            fail(out, "preflight needs --root")
            return 1
        import tempfile

        root = Path(tempfile.mkdtemp(prefix="sitewatch-"))
        limit = 200 if args.cmd == "fast" else 400
        stage(args.base, root, limit)
    findings, urls = scan(root, args.base, canon, allow_rows)
    if args.cmd == "nightly":
        geo = geometry_check([args.base], canon, available=False if args.offline else None)
        state["geometry"] = "skipped" if any(item.action == "skipped" for item in geo) else "ran"
        findings.extend(geo)
    else:
        state["geometry"] = ""
    state_mod.merge(state, findings, when.isoformat(timespec="seconds"), closed_rows)
    fixed = sum(1 for item in state["items"].values() if item.get("fixed_at") == when.isoformat(timespec="seconds"))
    write_outputs(out, findings, urls, canon_path, args.cmd, state, allow_rows, when)
    blocking = [
        item
        for item in findings
        if not item.allowlist and item.action != "skipped" and item.severity in {"critical", "high"}
    ]
    real = [item for item in findings if not item.allowlist and item.action != "skipped"]
    new = state.get("new_count") or 0
    confirmed = max(0, len(real) - new)
    subject = commit_subject(when, new, confirmed, fixed, state.get("critical_count") or 0)
    print(f"SITEWATCH_SUBJECT {subject}")
    if args.cmd == "preflight":
        word = _ru_count(len(real))
        critical = sum(1 for item in real if item.severity == "critical")
        if blocking:
            print(
                f"preflight: {len(real)} {word} ({critical} critical) — выкладка запрещена",
                file=sys.stderr,
            )
            return 1
        print(f"preflight: {len(real)} {word} — можно выкладывать", file=sys.stderr)
        return 0
    return 0


def _ru_count(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "находка"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "находки"
    return "находок"


if __name__ == "__main__":
    sys.exit(main())

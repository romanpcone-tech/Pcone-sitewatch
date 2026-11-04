"""Acceptance tests from Cursor brief v2."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

from pcone_sitewatch.allowlist import load as load_allow
from pcone_sitewatch.allowlist import match, parse_text, stale
from pcone_sitewatch.canon import load
from pcone_sitewatch.engine import scan
from pcone_sitewatch.geometry import check as geometry_check
from pcone_sitewatch.geometry import is_clean
from pcone_sitewatch.htmlutil import Page
from pcone_sitewatch.report import digest_line, render
from pcone_sitewatch.rules import hours_text
from pcone_sitewatch.rules.hourslib import read_visible, visible_problem

ROOT = Path(__file__).resolve().parents[1]
BROKEN = ROOT / "tests" / "fixtures" / "broken"
FIXED = ROOT / "tests" / "fixtures" / "fixed"
EXPECTED = json.loads((ROOT / "tests" / "expected.json").read_text(encoding="utf-8"))
BASE = "https://pconelab.co.il"
PY = sys.executable


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([PY, "-m", "pcone_sitewatch", *args], cwd=ROOT, capture_output=True, text=True)


def _keys(out: Path) -> set[tuple[str, str]]:
    lines = (out / "findings.jsonl").read_text(encoding="utf-8").splitlines()
    found = set()
    for line in lines:
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("allowlist") or item.get("action") == "skipped":
            continue
        found.add((item["rule_id"], item["url"]))
    return found


def test_preflight_broken_matches_expected(tmp_path: Path):
    proc = _run(["preflight", "--root", str(BROKEN), "--base", BASE, "--out", str(tmp_path), "--offline"])
    assert proc.returncode == 1, proc.stderr + proc.stdout
    got = _keys(tmp_path)
    want = {(item["rule_id"], item["url"]) for item in EXPECTED["findings"]}
    assert got == want, f"extra={got - want} missing={want - got}"
    assert len(got) >= 15
    assert "выкладка запрещена" in proc.stderr


def test_preflight_fixed_is_clean(tmp_path: Path):
    proc = _run(["preflight", "--root", str(FIXED), "--base", BASE, "--out", str(tmp_path), "--offline"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    text = (tmp_path / "findings.jsonl").read_text(encoding="utf-8").strip()
    assert text == ""
    assert "можно выкладывать" in proc.stderr


def test_verify_worse(tmp_path: Path):
    before = tmp_path / "before.json"
    before.write_text(json.dumps({"findings": []}), encoding="utf-8")
    pages = tmp_path / "pages.txt"
    pages.write_text("ru/hours.html\n", encoding="utf-8")
    proc = _run(
        ["verify", "--root", str(BROKEN), "--before", str(before), "--pages", str(pages), "--base", BASE]
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "reverted:" in proc.stdout
    assert "ru/hours.html" in proc.stdout


def test_watch_silence_old_state(tmp_path: Path):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"last_run": "2026-01-01T00:00:00+02:00"}), encoding="utf-8")
    proc = _run(["watch-silence", "--state", str(state), "--max-age", "26h"])
    assert proc.returncode == 1
    assert "сторож молчит: последний прогон" in proc.stdout


def test_watch_silence_fresh(tmp_path: Path):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    stamp = datetime.now(ZoneInfo("Asia/Jerusalem")).isoformat(timespec="seconds")
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"last_run": stamp}), encoding="utf-8")
    proc = _run(["watch-silence", "--state", str(state), "--max-age", "26h"])
    assert proc.returncode == 0
    assert "сторож молчит" not in proc.stdout


def test_allowlist_without_reason_keeps_finding(tmp_path: Path):
    allow = tmp_path / "allow.txt"
    url = BASE + "/ru/hours.html"
    allow.write_text(f"HOURS_TEXT | {url} |  | Roman, 2026-11-04\n", encoding="utf-8")
    rows, ignored = parse_text(allow.read_text(encoding="utf-8"))
    assert rows == []
    assert ignored
    proc = _run(
        ["preflight", "--root", str(BROKEN), "--base", BASE, "--out", str(tmp_path / "out"), "--allow", str(allow), "--offline"]
    )
    assert proc.returncode == 1
    got = _keys(tmp_path / "out")
    assert ("HOURS_TEXT", url) in got


def test_allowlist_with_reason_hides_one(tmp_path: Path):
    allow = tmp_path / "allow.txt"
    url = BASE + "/ru/hours.html"
    allow.write_text(
        f"HOURS_TEXT | {url} | owner keeps this hours line | Roman, 2026-11-04\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    proc = _run(["preflight", "--root", str(BROKEN), "--base", BASE, "--out", str(out), "--allow", str(allow), "--offline"])
    report = (out / "report.html").read_text(encoding="utf-8")
    assert "скрыто по allowlist: 1" in report
    rows = [json.loads(line) for line in (out / "findings.jsonl").read_text(encoding="utf-8").splitlines() if line]
    hidden = [row for row in rows if row["rule_id"] == "HOURS_TEXT"]
    assert hidden and hidden[0]["allowlist"] is True
    assert proc.returncode == 1


def test_glob_line_is_ignored():
    rows, ignored = parse_text("HOURS_TEXT | https://pconelab.co.il/* | reason | Roman, 2026-11-04\n")
    assert rows == []
    assert ignored


def test_mobile_overflow_without_browser_is_skipped():
    canon = load()
    found = geometry_check(["https://pconelab.co.il/"], canon, available=False)
    assert found
    assert found[0].action == "skipped"
    assert found[0].rule_id == "MOBILE_OVERFLOW"
    assert is_clean(found) is False


def test_canon_edit_changes_hours_without_code_edit(tmp_path: Path):
    canon = load()
    html = (
        '<html><body><p class="p7c-hours">Вс 10:00-18:00 · Пн-Чт 10:00-19:00 · '
        "Пт 09:00-14:00 · Сб закрыто · перерыв 13:30-15:00 (вс-чт)</p></body></html>"
    )
    page = Page(BASE + "/ru/hours.html", "ru/hours.html", html, tmp_path, tmp_path / "x.html")
    assert hours_text.check(page, canon)
    edited = json.loads(json.dumps(canon))
    edited["hours"]["sun"]["open"] = "10:00"
    edited["hours"]["sun"]["close"] = "18:00"
    assert hours_text.check(page, edited) == []
    good = Page(
        page.url,
        page.rel,
        html.replace("10:00-18:00", "09:00-19:00"),
        tmp_path,
        page.path,
    )
    assert hours_text.check(good, canon) == []
    assert hours_text.check(good, edited)


def test_hebrew_break_label_is_a_defect():
    canon = load()
    bad = "א׳ 09:00-19:00 · ב׳-ה׳ 10:00-19:00 (הפסקה 13:30-15:00) · ו׳ 09:00-14:00 · שבת סגור"
    good = "א׳ 09:00-19:00 · ב׳-ה׳ 10:00-19:00 · ו׳ 09:00-14:00 · שבת סגור · הפסקה 13:30-15:00 (א׳-ה׳)"
    assert visible_problem(read_visible(bad, canon), canon)
    assert visible_problem(read_visible(good, canon), canon) is None


def test_each_rule_positive_and_negative(tmp_path: Path):
    canon = load()
    allow, _ignored = load_allow(ROOT / "sitewatch" / "allowlist.txt")
    broken, _n = scan(BROKEN, BASE, canon, allow)
    fixed, _m = scan(FIXED, BASE, canon, allow)
    by_rule: dict[str, list] = {}
    for item in broken:
        if not item.allowlist:
            by_rule.setdefault(item.rule_id, []).append(item)
    for rule in (
        "HOURS_TEXT",
        "HOURS_JSONLD",
        "CONTACT",
        "META_PRICE",
        "PRICE_FACT",
        "BANNED_CLAIM",
        "OLD_HEADER",
        "WARRANTY_RU",
        "FREE_CLAIM",
        "ASSET_404",
        "LINK_BROKEN",
        "LANG_404",
        "HREFLANG",
        "CACHE_BUST",
        "JSONLD",
        "PAGE_4XX",
    ):
        assert by_rule.get(rule), rule
    assert fixed == []


def test_footer_used_link_is_not_a_banned_claim(tmp_path: Path):
    from pcone_sitewatch.rules import banned_claim

    canon = load()
    html = '<html><body><a href="https://buy2sell.co.il">Б/у техника</a></body></html>'
    page = Page(BASE + "/x.html", "x.html", html, tmp_path, tmp_path / "x.html")
    assert banned_claim.check(page, canon) == []
    html = "<html><body><p>trade-in today</p></body></html>"
    page = Page(BASE + "/y.html", "y.html", html, tmp_path, tmp_path / "y.html")
    assert banned_claim.check(page, canon)


def test_gta_rp_is_report_only_not_allowlist(tmp_path: Path):
    from pcone_sitewatch.engine import annotate
    from pcone_sitewatch.finding import Finding

    canon = load()
    rows, _ignored = load_allow(ROOT / "sitewatch" / "allowlist.txt")
    finding = Finding(
        rule_id="BANNED_CLAIM",
        severity="critical",
        url=BASE + "/ru/gta-rp.html",
        evidence="trade-in",
    )
    annotate([finding], [], canon, rows)
    assert finding.allowlist is False
    assert finding.severity == "info"
    assert finding.action == "report_only"
    assert match(rows, "*", BASE + "/ru/gta-rp.html") is None


def test_digest_one_line_and_not_clean_on_failure():
    clean = digest_line({"status": "ok", "urls_checked": 16, "new_count": 0, "critical_count": 0, "geometry": ""})
    failed = digest_line({"status": "failed", "fail_reason": "boom"})
    assert "\n" not in clean
    assert len(clean) <= 140
    assert clean.startswith("Сторож: всё чисто")
    assert failed.startswith("Сторож: прогон не прошёл")
    assert "всё чисто" not in failed


def test_findings_have_schema_fields(tmp_path: Path):
    schema = json.loads((ROOT / "schema" / "findings.schema.json").read_text(encoding="utf-8"))
    proc = _run(["preflight", "--root", str(BROKEN), "--base", BASE, "--out", str(tmp_path), "--offline"])
    assert proc.returncode == 1
    required = schema["required"]
    for line in (tmp_path / "findings.jsonl").read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        for key in required:
            assert key in item
        assert item["action"] in schema["properties"]["action"]["enum"]


def test_stale_allowlist_listed_on_sunday():
    rows, _ignored = parse_text("OLD_HEADER | https://pconelab.co.il/old.html | kept | Roman, 2026-01-01\n")
    old = stale(rows, date(2026, 11, 4), 60)
    assert old
    html = render([], 0, old, show_stale=True)
    assert "проверить, ещё задумано?" in html


def test_closed_and_published_parsers():
    from pcone_sitewatch.ron import is_newer, parse_closed, parse_published

    rows = parse_closed("# note\nabc123 2026-11-04 # fixed hours\n\n")
    assert rows == [("abc123", "2026-11-04")]
    assert parse_published("2026-11-04T23:04:48+02:00\n") is not None
    assert is_newer("2026-11-04T23:55:12+02:00", "2026-11-04T23:04:48+02:00")
    assert not is_newer("2026-11-04T23:04:48+02:00", "2026-11-04T23:04:48+02:00")


def test_meta_allows_only_diagnostics_200(tmp_path: Path):
    from pcone_sitewatch.rules import meta_price

    canon = load()
    ok = Page(
        BASE + "/a.html",
        "a.html",
        '<html><head><meta name="description" content="Диагностика 200 ₪."></head><body></body></html>',
        tmp_path,
        tmp_path / "a.html",
    )
    bad = Page(
        BASE + "/b.html",
        "b.html",
        '<html><head><meta name="description" content="Экран 350 ₪."></head><body></body></html>',
        tmp_path,
        tmp_path / "b.html",
    )
    assert meta_price.check(ok, canon) == []
    assert meta_price.check(bad, canon)


def test_contact_wrong_phone(tmp_path: Path):
    from pcone_sitewatch.rules import contact

    canon = load()
    bad = Page(
        BASE + "/c.html",
        "c.html",
        '<html><body><a href="tel:09-0000000">09-0000000</a></body></html>',
        tmp_path,
        tmp_path / "c.html",
    )
    good = Page(
        BASE + "/d.html",
        "d.html",
        '<html><body><a href="tel:09-8345676">09-8345676</a></body></html>',
        tmp_path,
        tmp_path / "d.html",
    )
    assert contact.check(bad, canon)
    assert contact.check(good, canon) == []

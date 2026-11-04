"""Read opening hours from visible text and JSON-LD using canon.json only."""

from __future__ import annotations

import json
import re

ORDER = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
SCHEMA = {
    "sun": "Sunday",
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
}
_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})\s*[-–—−]\s*(\d{1,2}):(\d{2})")
_CLOSED = re.compile(r"закрыт|closed|ferm|סגור|مغلق", re.I)
_HE_RANGE = re.compile(r"([אבגדהו])[׳'\u05f3\u2019]?\s*[-–—−]\s*([אבגדהו])[׳'\u05f3\u2019]?")
_HE = {"א": 0, "ב": 1, "ג": 2, "ד": 3, "ה": 4, "ו": 5}
_RANGES = [
    (re.compile(r"(?<![а-яё])вс\s*[-–—−]\s*чт(?![а-яё])", re.I), 0, 4),
    (re.compile(r"(?<![а-яё])пн\s*[-–—−]\s*чт(?![а-яё])", re.I), 1, 4),
    (re.compile(r"\bsun(?:day)?\s*[-–—−]\s*thu(?:rsday)?\b", re.I), 0, 4),
    (re.compile(r"\bmon(?:day)?\s*[-–—−]\s*thu(?:rsday)?\b", re.I), 1, 4),
    (re.compile(r"\bdim(?:anche)?\s*[-–—−]\s*jeu(?:di)?\b", re.I), 0, 4),
    (re.compile(r"\blun(?:di)?\s*[-–—−]\s*jeu(?:di)?\b", re.I), 1, 4),
    (re.compile(r"الأحد\s*[-–—−]\s*الخميس"), 0, 4),
    (re.compile(r"(?:الاثنين|الإثنين)\s*[-–—−]\s*الخميس"), 1, 4),
]
_SINGLES = [
    (re.compile(r"воскрес|(?<![а-яё])вс(?![а-яё])", re.I), "sun"),
    (re.compile(r"(?<![а-яё])пн(?![а-яё])", re.I), "mon"),
    (re.compile(r"(?<![а-яё])вт(?![а-яё])", re.I), "tue"),
    (re.compile(r"(?<![а-яё])ср(?![а-яё])", re.I), "wed"),
    (re.compile(r"(?<![а-яё])чт(?![а-яё])", re.I), "thu"),
    (re.compile(r"(?<![а-яё])пт(?![а-яё])", re.I), "fri"),
    (re.compile(r"(?<![а-яё])сб(?![а-яё])", re.I), "sat"),
    (re.compile(r"\bsunday\b|\bsun\b", re.I), "sun"),
    (re.compile(r"\bmonday\b|\bmon\b", re.I), "mon"),
    (re.compile(r"\btuesday\b|\btue\b", re.I), "tue"),
    (re.compile(r"\bwednesday\b|\bwed\b", re.I), "wed"),
    (re.compile(r"\bthursday\b|\bthu\b", re.I), "thu"),
    (re.compile(r"\bfriday\b|\bfri\b", re.I), "fri"),
    (re.compile(r"\bsaturday\b|\bsat\b", re.I), "sat"),
    (re.compile(r"\bdimanche\b|\bdim\b", re.I), "sun"),
    (re.compile(r"\blundi\b|\blun\b", re.I), "mon"),
    (re.compile(r"\bjeudi\b|\bjeu\b", re.I), "thu"),
    (re.compile(r"\bvendredi\b|\bven\b", re.I), "fri"),
    (re.compile(r"\bsamedi\b|\bsam\b", re.I), "sat"),
    (re.compile(r"ראשון"), "sun"),
    (re.compile(r"שישי"), "fri"),
    (re.compile(r"שבת"), "sat"),
    (re.compile(r"א[׳'\u05f3\u2019]"), "sun"),
    (re.compile(r"ב[׳'\u05f3\u2019]"), "mon"),
    (re.compile(r"ג[׳'\u05f3\u2019]"), "tue"),
    (re.compile(r"ד[׳'\u05f3\u2019]"), "wed"),
    (re.compile(r"ה[׳'\u05f3\u2019]"), "thu"),
    (re.compile(r"ו[׳'\u05f3\u2019]"), "fri"),
    (re.compile(r"الأحد"), "sun"),
    (re.compile(r"الاثنين|الإثنين"), "mon"),
    (re.compile(r"الخميس"), "thu"),
    (re.compile(r"الجمعة"), "fri"),
    (re.compile(r"السبت"), "sat"),
]


def _hh(h: str, m: str) -> str:
    return f"{int(h):02d}:{m}"


def canon_break(canon: dict) -> tuple[str, str]:
    pair = canon["hours"]["sun"]["break"]
    return pair[0], pair[1]


def segments(text: str) -> list[str]:
    parts = re.split(r"[·•|\n]+", text.replace("\xa0", " "))
    return [re.sub(r"\s+", " ", part).strip() for part in parts if part.strip()]


def _days(segment: str) -> set[str]:
    found: set[str] = set()
    for match in _HE_RANGE.finditer(segment):
        a = _HE.get(match.group(1))
        b = _HE.get(match.group(2))
        if a is None or b is None:
            continue
        if a > b:
            a, b = b, a
        for idx in range(a, b + 1):
            found.add(ORDER[idx])
    for pattern, start, end in _RANGES:
        if pattern.search(segment):
            for idx in range(start, end + 1):
                found.add(ORDER[idx])
    for pattern, day in _SINGLES:
        if pattern.search(segment):
            found.add(day)
    return found


def _spans(segment: str) -> list[tuple[str, str]]:
    return [(_hh(m.group(1), m.group(2)), _hh(m.group(3), m.group(4))) for m in _TIME.finditer(segment)]


def _norm_label(text: str) -> str:
    return (
        text.lower()
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("'", "׳")
        .replace("\u2019", "׳")
        .replace("\u05f3", "׳")
    )


def read_visible(text: str, canon: dict) -> dict:
    br = canon_break(canon)
    opens: dict[str, tuple[str, str]] = {}
    break_days: set[str] = set()
    break_ranges: list[tuple[str, str]] = []
    labelled_defect = False
    saw = False
    defect_labels = [_norm_label(item) for item in canon["hours"].get("defect_if_labelled") or []]
    for segment in segments(text):
        days = _days(segment)
        if days:
            saw = True
        spans = _spans(segment)
        norm = _norm_label(segment)
        has_break_span = br in spans
        if has_break_span and any(label in norm for label in defect_labels):
            labelled_defect = True
        if has_break_span:
            break_ranges.append(br)
            break_days |= days
            spans = [span for span in spans if span != br]
        if _CLOSED.search(segment) and "sat" in days and not spans:
            opens["sat"] = ("closed", "closed")
        for span in spans:
            for day in days:
                if day == "sat":
                    continue
                opens[day] = span
    return {
        "saw": saw,
        "opens": opens,
        "break_days": break_days,
        "break_ranges": break_ranges,
        "labelled_defect": labelled_defect,
        "sat_closed": opens.get("sat") == ("closed", "closed"),
    }


def visible_problem(read: dict, canon: dict) -> str | None:
    if not read["saw"]:
        return None
    hours = canon["hours"]
    sun = (hours["sun"]["open"], hours["sun"]["close"])
    mon = (hours["mon_thu"]["open"], hours["mon_thu"]["close"])
    fri = (hours["fri"]["open"], hours["fri"]["close"])
    expect = {"sun": sun, "mon": mon, "tue": mon, "wed": mon, "thu": mon, "fri": fri}
    bad = []
    for day, span in expect.items():
        if read["opens"].get(day) != span:
            got = read["opens"].get(day)
            shown = f"{got[0]}-{got[1]}" if got else "missing"
            bad.append(f"{day} {shown}")
    if hours.get("sat") == "closed" and not read["sat_closed"]:
        bad.append("saturday not closed")
    if read["labelled_defect"]:
        bad.append("break labelled " + "/".join(hours.get("defect_if_labelled") or []))
    needed = set(hours.get("break_weekdays") or [])
    if read["break_ranges"]:
        if not needed <= read["break_days"]:
            bad.append("break days " + ",".join(sorted(read["break_days"])))
        forbidden = set(hours.get("break_not_weekdays") or [])
        if forbidden & read["break_days"]:
            bad.append("break on " + ",".join(sorted(forbidden & read["break_days"])))
    elif read["saw"]:
        bad.append("lunch break missing")
    if not bad:
        return None
    return "; ".join(bad)


def expected_jsonld(canon: dict) -> dict[str, list[tuple[str, str]]]:
    hours = canon["hours"]

    def split(spec) -> list[tuple[str, str]]:
        if spec == "closed" or not isinstance(spec, dict):
            return []
        if spec.get("break"):
            return [(spec["open"], spec["break"][0]), (spec["break"][1], spec["close"])]
        return [(spec["open"], spec["close"])]

    out = {"Sunday": split(hours["sun"]), "Friday": split(hours["fri"])}
    for key in ("mon", "tue", "wed", "thu"):
        out[SCHEMA[key]] = split(hours["mon_thu"])
    out["Saturday"] = [] if hours.get("sat") == "closed" else split(hours.get("sat"))
    return out


def _day_name(value: str) -> str:
    return str(value).rstrip("/").split("/")[-1]


def collect_jsonld(blocks: list[dict]) -> dict[str, list[tuple[str, str]]] | None:
    found: dict[str, list[tuple[str, str]]] = {}
    saw = False
    for block in blocks:
        raw = block.get("raw") or ""
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            for value in node.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
            specs = node.get("openingHoursSpecification")
            if not specs:
                continue
            saw = True
            if isinstance(specs, dict):
                specs = [specs]
            for spec in specs:
                if not isinstance(spec, dict):
                    continue
                days = spec.get("dayOfWeek") or []
                if isinstance(days, str):
                    days = [days]
                span = (str(spec.get("opens") or ""), str(spec.get("closes") or ""))
                for day in days:
                    found.setdefault(_day_name(day), []).append(span)
    if not saw:
        return None
    return found


def jsonld_problem(blocks: list[dict], canon: dict) -> str | None:
    found = collect_jsonld(blocks)
    if found is None:
        return None
    expect = expected_jsonld(canon)
    bad = []
    for day, spans in expect.items():
        got = found.get(day, [])
        if sorted(got) != sorted(spans):
            shown = ", ".join(f"{a}-{b}" for a, b in got) or "missing"
            bad.append(f"{day}: {shown}")
    if not bad:
        return None
    return "; ".join(bad)

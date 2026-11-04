import re

from pcone_sitewatch.finding import Finding

# Words named in canon free_claims.note («бесплатно» / free). Not auto-fixed.
_TERMS = (
    re.compile(r"бесплатно", re.I),
    re.compile(r"(?<![a-z])free(?![a-z])", re.I),
)


def check(page, canon: dict) -> list[Finding]:
    note = (canon.get("free_claims") or {}).get("note") or ""
    if "бесплатно" not in note and "free" not in note.lower():
        return []
    visible = page.parsed()["visible"]
    hits = []
    for pattern in _TERMS:
        match = pattern.search(visible)
        if match:
            hits.append(match.group(0))
    if not hits:
        return []
    return [
        Finding(
            rule_id="FREE_CLAIM",
            severity="medium",
            url=page.url,
            file=page.rel,
            target="free",
            action="report_only",
            evidence="report only: " + ", ".join(hits),
        )
    ]

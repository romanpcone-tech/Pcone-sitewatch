import re

from pcone_sitewatch.finding import Finding


def check(page, canon: dict) -> list[Finding]:
    text = canon.get("warranty", {}).get("ru") or ""
    if not text:
        return []
    visible = page.parsed()["visible"]
    if "Гарантия" not in visible and "гарантия" not in visible.lower():
        return []
    folded = re.sub(r"\s+", " ", visible).strip()
    canon_folded = re.sub(r"\s+", " ", text).strip()
    if canon_folded in folded:
        return []
    return [
        Finding(
            rule_id="WARRANTY_RU",
            severity=canon["warranty"].get("severity") or "critical",
            url=page.url,
            file=page.rel,
            target="warranty",
            evidence=folded[:240],
        )
    ]

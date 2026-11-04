"""Structural detector: Arena header is header#hdr or header[data-arena].

A blue-strip element, or a header that is not that Arena header, is the old header.
The marker string is the structural class, not a sentence in the copy.
"""

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding


def check(page, canon: dict) -> list[Finding]:
    hits = page.parsed().get("blue_strip") or []
    if not hits:
        return []
    return [
        Finding(
            rule_id="OLD_HEADER",
            severity=severity(canon, "old header"),
            url=page.url,
            file=page.rel,
            target="header",
            evidence=hits[0],
        )
    ]

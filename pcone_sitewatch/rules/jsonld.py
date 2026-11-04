import json

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding


def check(page, canon: dict) -> list[Finding]:
    found = []
    for index, block in enumerate(page.parsed()["jsonld"]):
        raw = block.get("raw") or ""
        if not raw.strip():
            found.append(
                Finding(
                    rule_id="JSONLD",
                    severity=severity(canon, "JSON-LD invalid"),
                    url=page.url,
                    file=page.rel,
                    target=f"empty:{index}",
                    evidence="empty application/ld+json",
                )
            )
            continue
        try:
            json.loads(raw)
        except json.JSONDecodeError as exc:
            found.append(
                Finding(
                    rule_id="JSONLD",
                    severity=severity(canon, "JSON-LD invalid"),
                    url=page.url,
                    file=page.rel,
                    target=f"parse:{index}",
                    evidence=f"JSON does not parse: {exc.msg}",
                )
            )
    return found

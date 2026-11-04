import re

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding

_PRICE = re.compile(
    r"(?:₪\s*(\d{1,6})|(\d{1,6})\s*₪|(\d{1,6})\s*ILS\b)",
    re.I,
)


def _allowed_amounts(canon: dict) -> set[str]:
    item = canon["meta"]["only_allowed_price"]
    return {str(item.get("amount"))}


def offending(text: str, canon: dict) -> list[str]:
    allowed = _allowed_amounts(canon)
    bad = []
    for match in _PRICE.finditer(text or ""):
        number = next(group for group in match.groups() if group)
        if number not in allowed:
            bad.append(match.group(0).strip())
    return bad


def check(page, canon: dict) -> list[Finding]:
    view = page.parsed()
    fields = (
        ("description", "meta[name=description]"),
        ("og:description", "meta[property=og:description]"),
        ("twitter:description", "meta[name=twitter:description]"),
    )
    found = []
    for key, selector in fields:
        text = view["metas"].get(key) or ""
        bad = offending(text, canon)
        if not bad:
            continue
        found.append(
            Finding(
                rule_id="META_PRICE",
                severity=severity(canon, "price in meta"),
                url=page.url,
                file=page.rel,
                target=key,
                evidence=f"{selector}: " + ", ".join(bad),
            )
        )
    return found

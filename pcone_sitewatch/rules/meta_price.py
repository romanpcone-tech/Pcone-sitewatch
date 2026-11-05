import re

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding

_NUMBER = r"(?<![\d.,\u066b\u066c])(\d{1,3}(?:[,\u066c\u066b\u00a0 ]\d{3})+|\d{1,6})"
_PRICE = re.compile(
    rf"(?:₪\s*{_NUMBER}|{_NUMBER}\s*₪|{_NUMBER}\s*ILS\b)",
    re.I,
)


def _allowed_amounts(canon: dict) -> set[str]:
    item = canon["meta"]["only_allowed_price"]
    return {str(item.get("amount"))}


def offending(text: str, canon: dict) -> list[str]:
    allowed = _allowed_amounts(canon)
    bad = []
    for match in _PRICE.finditer(text or ""):
        # "3,056 ₪" must read as 3056, not as 056 (thousands separator).
        digits = re.sub(r"\D", "", match.group(0))
        if digits and digits not in allowed:
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

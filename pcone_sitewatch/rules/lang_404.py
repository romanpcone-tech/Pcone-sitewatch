from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import rel_for_url


def check(page, canon: dict) -> list[Finding]:
    missing = []
    for code, href in page.parsed()["hreflang"].items():
        if code == "x-default":
            continue
        rel = rel_for_url(href)
        if not (page.root / rel).is_file():
            missing.append(f"{code} {href}")
    if not missing:
        return []
    return [
        Finding(
            rule_id="LANG_404",
            severity=severity(canon, "missing language page"),
            url=page.url,
            file=page.rel,
            target="hreflang-missing",
            evidence="; ".join(missing),
        )
    ]

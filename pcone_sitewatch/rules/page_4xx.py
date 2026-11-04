import re

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import rel_for_url


def check(page, canon: dict) -> list[Finding]:
    return []


def from_sitemap(root, base: str, canon: dict) -> list[Finding]:
    sitemap = root / "sitemap.xml"
    if not sitemap.is_file():
        return []
    text = sitemap.read_text(encoding="utf-8")
    found = []
    for loc in re.findall(r"<loc>\s*([^<]+)\s*</loc>", text):
        rel = rel_for_url(loc.strip())
        if (root / rel).is_file():
            continue
        found.append(
            Finding(
                rule_id="PAGE_4XX",
                severity=severity(canon, "page 4xx/5xx"),
                url=loc.strip(),
                file=rel,
                target="sitemap",
                evidence=f"no file for {rel}",
            )
        )
    return found


def from_status(url: str, status: int, canon: dict, rel: str = "") -> list[Finding]:
    if status and status < 400:
        return []
    return [
        Finding(
            rule_id="PAGE_4XX",
            severity=severity(canon, "page 4xx/5xx"),
            url=url,
            file=rel,
            target=f"status:{status}",
            evidence=f"HTTP {status or 'error'}",
        )
    ]

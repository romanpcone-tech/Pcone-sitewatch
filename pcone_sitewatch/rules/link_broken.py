from urllib.parse import urlsplit

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import is_asset_ref, resolve_local


def check(page, canon: dict) -> list[Finding]:
    found = []
    host = urlsplit(page.url).netloc.lower().removeprefix("www.")
    for link in page.parsed()["links"]:
        raw = link["raw"]
        if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if is_asset_ref(raw):
            continue
        target = urlsplit(link["url"])
        if target.netloc and target.netloc.lower().removeprefix("www.") != host:
            continue
        local = resolve_local(page.root, page.path, raw, page.url)
        if local is None or local.is_file():
            continue
        found.append(
            Finding(
                rule_id="LINK_BROKEN",
                severity=severity(canon, "broken link"),
                url=page.url,
                file=page.rel,
                target=raw,
                evidence=f"missing {raw}",
            )
        )
        break
    return found

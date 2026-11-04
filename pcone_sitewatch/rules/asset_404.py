from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import is_asset_ref, resolve_local


def check(page, canon: dict) -> list[Finding]:
    found = []
    seen = set()
    for asset in page.parsed()["assets"]:
        raw = asset["raw"]
        if not is_asset_ref(raw):
            continue
        local = resolve_local(page.root, page.path, raw, page.url)
        if local is None or local.is_file():
            continue
        if raw in seen:
            continue
        seen.add(raw)
        found.append(
            Finding(
                rule_id="ASSET_404",
                severity=severity(canon, "broken asset"),
                url=page.url,
                file=page.rel,
                target=raw,
                evidence=f"missing {raw}",
            )
        )
    return found

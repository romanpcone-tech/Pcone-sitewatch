import re
from urllib.parse import urlsplit

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import is_asset_ref, resolve_local

_HASH = re.compile(r"[-.][a-f0-9]{6,}", re.I)
_CODE = (".css", ".js", ".mjs")


def check(page, canon: dict) -> list[Finding]:
    found = []
    for asset in page.parsed()["assets"]:
        raw = asset["raw"]
        path = urlsplit(raw).path.lower()
        if not path.endswith(_CODE):
            continue
        if not is_asset_ref(raw) and not path.endswith(_CODE):
            continue
        local = resolve_local(page.root, page.path, raw, page.url)
        if local is None or not local.is_file():
            continue
        query = urlsplit(raw).query
        name = path.rsplit("/", 1)[-1]
        if "v=" in query or _HASH.search(name):
            continue
        found.append(
            Finding(
                rule_id="CACHE_BUST",
                severity=severity(canon, "cache-bust missing"),
                url=page.url,
                file=page.rel,
                target=raw,
                evidence=f"no ?v= or hash in {raw}",
            )
        )
        break
    return found

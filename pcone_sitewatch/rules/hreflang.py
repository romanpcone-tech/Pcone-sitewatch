"""Existing language siblings must be listed. Missing targets are LANG_404."""

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import norm_url, url_for_rel

_PREFIXES = ("", "ru/", "en/", "fr/", "ar/", "he/")


def _siblings(page) -> list[str]:
    from urllib.parse import urlsplit

    name = page.rel.split("/")[-1]
    parts = urlsplit(page.url)
    origin = f"{parts.scheme}://{parts.netloc}"
    urls = []
    for prefix in _PREFIXES:
        candidate = prefix + name
        if (page.root / candidate).is_file():
            urls.append(url_for_rel(origin, candidate))
    return urls


def check(page, canon: dict) -> list[Finding]:
    declared = page.parsed()["hreflang"]
    if not declared:
        return []
    declared_norm = {norm_url(href) for href in declared.values()}
    missing = []
    for url in _siblings(page):
        if norm_url(url) not in declared_norm and norm_url(url) != norm_url(page.url):
            # self may be listed; if self isn't listed but file is self, still a sibling
            if norm_url(url) == norm_url(page.url):
                continue
            missing.append(url)
    # self is a sibling; it does not have to be re-listed if we only care about others
    if not missing:
        return []
    return [
        Finding(
            rule_id="HREFLANG",
            severity=severity(canon, "hreflang mismatch"),
            url=page.url,
            file=page.rel,
            target="hreflang-set",
            evidence="existing page not in hreflang: " + ", ".join(missing),
        )
    ]

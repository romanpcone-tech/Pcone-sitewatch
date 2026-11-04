"""Stage a slice of the live site into a temp tree. GET/HEAD only."""

from __future__ import annotations

import re
from pathlib import Path

from pcone_sitewatch.htmlutil import is_asset_ref, parse_html, rel_for_url
from pcone_sitewatch.net import Client


def stage(base: str, dest: Path, limit: int) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    client = Client()
    status, xml = client.get_text(base.rstrip("/") + "/sitemap.xml")
    if status != 200:
        return 0
    locs = re.findall(r"<loc>\s*([^<]+)\s*</loc>", xml)
    homes = [base.rstrip("/") + path for path in ("/", "/ru/", "/en/", "/fr/", "/ar/", "/he/")]
    ordered = []
    for url in homes + locs:
        if url not in ordered:
            ordered.append(url)
    pages = ordered[:limit]
    asset_urls = []
    link_urls = []
    written = 0
    for url in pages:
        status, body = client.get_text(url)
        if status != 200 or "<html" not in body.lower() and "<!doctype" not in body.lower():
            continue
        rel = rel_for_url(url)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        written += 1
        view = parse_html(body, url)
        for asset in view["assets"]:
            if is_asset_ref(asset["raw"]):
                asset_urls.append(asset["url"])
        for link in view["links"]:
            link_urls.append(link["url"])
        for href in view["hreflang"].values():
            link_urls.append(href)
    seen = set()
    for url in asset_urls + link_urls:
        if url in seen or not url.startswith(base):
            continue
        seen.add(url)
        rel = rel_for_url(url)
        target = dest / rel
        if target.exists():
            continue
        status, _headers, _body, _err = client.request(url, method="HEAD", timeout=12)
        if 200 <= status < 400:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text("", encoding="utf-8")
    return written

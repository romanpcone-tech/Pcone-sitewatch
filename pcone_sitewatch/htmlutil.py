"""Small HTML helpers. Facts are not stored here."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

ASSET_MARKERS = ("/css/", "/assets/", "/img/", "/js/", "css/", "assets/", "img/", "js/")


def norm_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1] or "/"
    if path.endswith("/index.html"):
        path = path[: -len("index.html")] or "/"
        if path != "/" and path.endswith("/"):
            path = path[:-1] or "/"
    return urlunsplit(("https", host, path if path.startswith("/") else "/" + path, "", ""))


def url_for_rel(base: str, rel: str) -> str:
    rel = rel.replace("\\", "/").lstrip("/")
    root = base.rstrip("/")
    if rel in ("", "index.html"):
        return root + "/"
    return root + "/" + rel


def rel_for_url(url: str) -> str:
    path = urlsplit(url).path or "/"
    if path in ("", "/"):
        return "index.html"
    if path.endswith("/"):
        return path.strip("/") + "/index.html"
    return path.lstrip("/")


def is_asset_ref(raw: str) -> bool:
    value = (raw or "").split("?", 1)[0].split("#", 1)[0]
    lower = value.lower()
    return any(marker in lower for marker in ("/css/", "/assets/", "/img/", "/js/")) or any(
        lower.startswith(marker) for marker in ("css/", "assets/", "img/", "js/")
    )


def resolve_local(root: Path, page_path: Path, raw: str, page_url: str) -> Path | None:
    raw = (raw or "").strip()
    if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    absolute = urljoin(page_url, raw)
    parts = urlsplit(absolute)
    if parts.scheme in ("http", "https") and parts.netloc and norm_url(absolute).split("/")[2] not in norm_url(page_url):
        # external host
        page_host = urlsplit(norm_url(page_url)).netloc
        if parts.netloc.lower().removeprefix("www.") != page_host:
            return None
    rel = rel_for_url(absolute)
    full = (root / rel).resolve()
    try:
        full.relative_to(root.resolve())
    except ValueError:
        return None
    return full


@dataclass
class Page:
    url: str
    rel: str
    html: str
    root: Path
    path: Path
    view: dict = field(default_factory=dict)

    def parsed(self) -> dict:
        if not self.view:
            self.view = parse_html(self.html, self.url)
        return self.view


class _Parser(HTMLParser):
    def __init__(self, page_url: str):
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.skip = 0
        self.visible: list[str] = []
        self.hours: list[dict] = []
        self.hours_depth = 0
        self.hours_buf: list[str] = []
        self.hours_line = 0
        self.metas: dict[str, str] = {}
        self.links: list[dict] = []
        self.assets: list[dict] = []
        self.hreflang: dict[str, str] = {}
        self.jsonld: list[dict] = []
        self.in_json = False
        self.json_buf: list[str] = []
        self.json_line = 0
        self.emails: list[str] = []
        self.tels: list[str] = []
        self.header_tags: list[str] = []
        self.blue_strip: list[str] = []
        self._anchor: dict | None = None

    def handle_starttag(self, tag, attrs):
        attr = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        classes = set((attr.get("class") or "").split())
        line = self.getpos()[0]
        if tag == "script" and "ld+json" in attr.get("type", "").lower():
            self.in_json = True
            self.json_buf = []
            self.json_line = line
            return
        if tag in {"script", "style"}:
            self.skip += 1
            return
        if tag == "header":
            self.header_tags.append(attr.get("id", "") + " " + attr.get("class", "") + " " + ("data-arena" if "data-arena" in attr else ""))
            if attr.get("id") != "hdr" and "data-arena" not in attr:
                self.blue_strip.append(f"<header> without Arena marker at line {line}")
        blob = (attr.get("class", "") + " " + attr.get("id", "")).lower()
        if "blue-strip" in blob or "bluestrip" in blob:
            self.blue_strip.append(f"blue-strip element <{tag}> at line {line}")
        if "p7c-hours" in classes or "hours" in classes:
            if self.hours_depth == 0:
                self.hours_buf = []
                self.hours_line = line
            self.hours_depth += 1
        if tag == "meta":
            name = attr.get("name", "").lower()
            prop = attr.get("property", "").lower()
            content = attr.get("content", "")
            if name == "description":
                self.metas["description"] = content
            elif prop == "og:description":
                self.metas["og:description"] = content
            elif name == "twitter:description":
                self.metas["twitter:description"] = content
        if tag == "link":
            rels = set(attr.get("rel", "").lower().split())
            href = attr.get("href", "")
            if "alternate" in rels and attr.get("hreflang"):
                self.hreflang[attr["hreflang"].strip().lower()] = urljoin(self.page_url, href)
            if href and ("stylesheet" in rels or is_asset_ref(href)):
                self.assets.append({"raw": href, "url": urljoin(self.page_url, href), "line": line})
        if tag == "a":
            href = attr.get("href", "")
            self._anchor = {"raw": href, "url": urljoin(self.page_url, href) if href else "", "line": line, "text": []}
            if href.lower().startswith("mailto:"):
                self.emails.append(href.split(":", 1)[1].split("?", 1)[0])
            if href.lower().startswith("tel:"):
                self.tels.append(href.split(":", 1)[1])
        if tag in {"script", "img", "source"} and attr.get("src"):
            src = attr["src"]
            if is_asset_ref(src) or tag == "script":
                self.assets.append({"raw": src, "url": urljoin(self.page_url, src), "line": line})

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "script" and self.in_json:
            self.jsonld.append({"raw": "".join(self.json_buf).strip(), "line": self.json_line})
            self.in_json = False
            return
        if tag in {"script", "style"} and self.skip:
            self.skip -= 1
            return
        if tag == "tr" and self.hours_depth:
            self.hours_buf.append("\n")
        if self.hours_depth and tag in {"p", "div", "table", "section", "span"}:
            # depth is counted on start; close when the hours element ends is approximate
            pass
        if self.hours_depth:
            self.hours_depth -= 1
            if self.hours_depth <= 0:
                text = re.sub(r"[ \t]+", " ", "".join(self.hours_buf))
                text = re.sub(r" *\n *", "\n", text).strip()
                if text:
                    self.hours.append({"text": text, "line": self.hours_line})
                self.hours_depth = 0
                self.hours_buf = []
        if tag == "a" and self._anchor is not None:
            self._anchor["text"] = "".join(self._anchor["text"]).strip()
            self.links.append(self._anchor)
            self._anchor = None

    def handle_data(self, data):
        if self.in_json:
            self.json_buf.append(data)
            return
        if self.skip:
            return
        if self._anchor is not None:
            self._anchor["text"].append(data)
        if data.strip():
            self.visible.append(data)
            if self.hours_depth:
                self.hours_buf.append(data)


def _hours_blocks(html: str) -> list[dict]:
    blocks = []
    pattern = re.compile(
        r"<(p|div|table|span|section)\b([^>]*)>(.*?)</\1>",
        re.I | re.S,
    )
    for match in pattern.finditer(html or ""):
        attrs = match.group(2)
        if not re.search(r"""class\s*=\s*['"][^'"]*\bhours\b[^'"]*['"]""", attrs, re.I) and not re.search(
            r"""class\s*=\s*['"][^'"]*p7c-hours[^'"]*['"]""", attrs, re.I
        ):
            continue
        text = re.sub(r"<[^>]+>", " ", match.group(3))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            line = html[: match.start()].count("\n") + 1
            blocks.append({"text": text, "line": line})
    return blocks


def parse_html(html: str, page_url: str) -> dict:
    parser = _Parser(page_url)
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        pass
    visible = re.sub(r"\s+", " ", " ".join(parser.visible)).strip()
    hours = _hours_blocks(html or "") or parser.hours
    return {
        "visible": visible,
        "hours": hours,
        "metas": parser.metas,
        "links": parser.links,
        "assets": parser.assets,
        "hreflang": parser.hreflang,
        "jsonld": parser.jsonld,
        "emails": parser.emails,
        "tels": parser.tels,
        "blue_strip": parser.blue_strip,
    }


def load_tree(root: Path, base: str) -> list[Page]:
    pages = []
    for path in sorted(root.rglob("*.html")):
        rel = path.relative_to(root).as_posix()
        html = path.read_text(encoding="utf-8")
        pages.append(Page(url_for_rel(base, rel), rel, html, root, path))
    return pages

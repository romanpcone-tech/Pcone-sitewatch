import re

from pcone_sitewatch.allowlist import allowed_anchor_texts
from pcone_sitewatch.finding import Finding


def _strip_allowed_anchors(html: str, anchors: list[str]) -> str:
    cleaned = html
    for text in anchors:
        cleaned = re.sub(
            rf"<a\b[^>]*>\s*{re.escape(text)}\s*</a>",
            " ",
            cleaned,
            flags=re.I,
        )
    return cleaned


def check(page, canon: dict) -> list[Finding]:
    anchors = allowed_anchor_texts(canon)
    html = _strip_allowed_anchors(page.html or "", anchors)
    visible = re.sub(r"<[^>]+>", " ", html)
    visible = re.sub(r"\s+", " ", visible)
    for item in canon.get("banned") or []:
        if item.get("id") == "old_header_blue_strip":
            continue
        for pattern in item.get("patterns") or []:
            if pattern.lower() in visible.lower():
                return [
                    Finding(
                        rule_id="BANNED_CLAIM",
                        severity=item.get("severity") or "critical",
                        url=page.url,
                        file=page.rel,
                        target=item.get("id") or pattern,
                        evidence=pattern,
                    )
                ]
    return []

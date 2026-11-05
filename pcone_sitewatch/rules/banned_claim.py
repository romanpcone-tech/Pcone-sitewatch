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


_NEGATION = re.compile(
    r"не\s+(?:явля|авториз|офиц|представ)|независим|неофиц|неавториз"
    r"|\bnot\s+(?:an?\s+)?(?:authori[sz]ed|official|independent|apple)\b|\bindependent\b"
    r"|\bunauthori[sz]ed\b|\bnon[-\s]?authori[sz]ed\b"
    r"|איננו|אינו|אינה|אינם|לא\s+(?:מעבדה|מורש|שירות|נציג)|בלתי[\s-]*מורש|עצמאי|עצמאית"
    r"|\bغير\s+(?:مورخ|مفوض|رسمي)|لسنا"
    r"|\bpas\s+(?:un\s+)?(?:service|centre|center|officiel)|\bindépendant\b|\bnon\s+autorisé\b",
    re.I,
)
_NEG_BEFORE = 90
_NEG_AFTER = 120


def _negated(visible: str, start: int, end: int) -> bool:
    """True when the claim sits in a negated context ("Нет, мы не авторизованный сервис")."""
    window = visible[max(0, start - _NEG_BEFORE) : end + _NEG_AFTER]
    return bool(_NEGATION.search(window))


def check(page, canon: dict) -> list[Finding]:
    anchors = allowed_anchor_texts(canon)
    html = _strip_allowed_anchors(page.html or "", anchors)
    visible = re.sub(r"<[^>]+>", " ", html)
    visible = re.sub(r"\s+", " ", visible)
    low = visible.lower()
    for item in canon.get("banned") or []:
        if item.get("id") == "old_header_blue_strip":
            continue
        for pattern in item.get("patterns") or []:
            needle = pattern.lower()
            pos = low.find(needle)
            while pos != -1:
                if not _negated(visible, pos, pos + len(needle)):
                    return [
                        Finding(
                            rule_id="BANNED_CLAIM",
                            severity=item.get("severity") or "critical",
                            url=page.url,
                            file=page.rel,
                            target=item.get("id") or pattern,
                            evidence=pattern + " | " + visible[max(0, pos - 60) : pos + len(needle) + 60].strip(),
                        )
                    ]
                pos = low.find(needle, pos + 1)
    return []

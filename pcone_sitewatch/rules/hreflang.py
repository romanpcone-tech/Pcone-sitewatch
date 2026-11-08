"""Existing language siblings must be listed. Missing targets are LANG_404.

08.11.2026: siblings искались только в корне сайта (`page.root / "ru/" + name`), поэтому
для страницы подраздела (`apple/about.html`) правильные адреса `apple/ru/about.html`
объявлялись «отсутствующими» — 100 ложных находок high на живом.

Второй заход (ревью 08.11): язык нельзя вставлять «перед именем файла» — в части разделов
после него ещё есть каталоги (`parts/fr/p/a33-k55/index.html`, `bconnect/shop-v2/ru/x.html`).
Теперь запоминается ПОЗИЦИЯ языкового сегмента в пути, и язык подставляется ровно туда же;
для страниц без языкового сегмента проверяются оба ходовых варианта (язык в начале и после
первого каталога раздела) — структура сайта неоднородна.
"""

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.htmlutil import norm_url, url_for_rel

_LANGS = ("ru", "en", "fr", "ar", "he")


def _split_rel(rel: str) -> tuple[int | None, list[str], str]:
    """Путь -> (позиция языкового сегмента или None, каталоги без него, имя файла)."""
    parts = rel.split("/")
    for i in range(len(parts) - 1):          # имя файла языком не считаем
        if parts[i] in _LANGS:
            return i, parts[:i] + parts[i + 1:-1], parts[-1]
    return None, parts[:-1], parts[-1]


def _candidates(lang_pos: int | None, dirs: list[str], name: str) -> list[str]:
    """Все правдоподобные пути перевода: тот же раздел, другой/пустой языковой сегмент."""
    out = []
    if lang_pos is not None:
        for lang in ("",) + _LANGS:
            segs = dirs[:lang_pos] + ([lang] if lang else []) + dirs[lang_pos:] + [name]
            out.append("/".join(segs))
    else:
        out.append("/".join(dirs + [name]))
        for lang in _LANGS:
            out.append("/".join([lang] + dirs + [name]))
            if dirs:
                out.append("/".join(dirs + [lang] + [name]))
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _siblings(page) -> list[str]:
    from urllib.parse import urlsplit

    lang_pos, dirs, name = _split_rel(page.rel)
    parts = urlsplit(page.url)
    origin = f"{parts.scheme}://{parts.netloc}"
    urls = []
    for candidate in _candidates(lang_pos, dirs, name):
        if candidate == page.rel:
            continue
        if (page.root / candidate).is_file():
            url = url_for_rel(origin, candidate)
            if url not in urls:
                urls.append(url)
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

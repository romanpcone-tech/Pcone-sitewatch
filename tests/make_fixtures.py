"""Build the broken and fixed mini-sites. Run from the repo root."""

from __future__ import annotations

import json
from pathlib import Path

from pcone_sitewatch.canon import load
from pcone_sitewatch.rules.hourslib import expected_jsonld

ROOT = Path(__file__).resolve().parent / "fixtures"
BASE = "https://pconelab.co.il"
CANON = load()
WARRANTY = CANON["warranty"]["ru"]


def page(lang: str, title: str, body: str, extra_head: str = "", css: str = "/css/base-a1b2c3d4.css", header: str = "") -> str:
    if not header:
        header = '<header id="hdr" data-arena="3d"><a href="/index.html">PCone</a></header>'
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="description" content="Independent repair lab in Netanya.">
<link rel="stylesheet" href="{css}">
{extra_head}
</head>
<body>
{header}
<main>
<h1>{title}</h1>
{body}
</main>
</body>
</html>
"""


def hours_block(text: str) -> str:
    return f'<p class="p7c-hours">{text}</p>'


GOOD_HOURS = "Вс 09:00-19:00 · Пн-Чт 10:00-19:00 · Пт 09:00-14:00 · Сб закрыто · перерыв 13:30-15:00 (вс-чт)"
BAD_HOURS = "Вс 09:00-19:00 · Пн-Чт 10:00-19:00 (перерыв 13:30-15:00) · Пт 09:00-14:00 · Сб закрыто"


def jsonld(specs: list[dict]) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "ComputerStore",
        "name": "PCone",
        "openingHoursSpecification": specs,
    }
    return '<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False) + "</script>"


def good_specs() -> list[dict]:
    specs = []
    for day, spans in expected_jsonld(CANON).items():
        for opens, closes in spans:
            specs.append(
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": day,
                    "opens": opens,
                    "closes": closes,
                }
            )
    return specs


def bad_specs() -> list[dict]:
    return [
        {
            "@type": "OpeningHoursSpecification",
            "dayOfWeek": "Sunday",
            "opens": "09:00",
            "closes": "19:00",
        }
    ]


def write_tree(dest: Path, broken: bool) -> None:
    if dest.exists():
        for path in sorted(dest.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "css").mkdir(exist_ok=True)
    (dest / "css" / "base-a1b2c3d4.css").write_text("/* fixture */\n", encoding="utf-8")
    (dest / "css" / "plain.css").write_text("/* plain */\n", encoding="utf-8")
    files: dict[str, str] = {}
    files["index.html"] = page("en", "PCone", "<p>Lab</p>")
    files["ru/hours.html"] = page("ru", "Hours", hours_block(BAD_HOURS if broken else GOOD_HOURS))
    specs = bad_specs() if broken else good_specs()
    files["ru/hours-json.html"] = page("ru", "Hours JSON", "<p>Schedule data.</p>", extra_head=jsonld(specs))
    if broken:
        contact = page("en", "Contact", '<p><a href="mailto:info@pconelab.co.il">info@pconelab.co.il</a></p>')
    else:
        contact = page("en", "Contact", '<p><a href="mailto:ron@pcone.co.il">ron@pcone.co.il</a></p>')
    files["en/contact.html"] = contact
    if broken:
        meta = page("en", "Meta", "<p>No price in the body.</p>")
        meta = meta.replace(
            'content="Independent repair lab in Netanya."',
            'content="Diagnostics note 350 ₪ in the description."',
        )
    else:
        meta = page("en", "Meta", "<p>No price in the body.</p>")
    files["en/meta.html"] = meta
    price = "диагностика 999 ₪" if broken else "диагностика 200 ₪"
    files["ru/price.html"] = page("ru", "Price", f"<p>{price}</p>")
    banned = "срочная диагностика" if broken else "с 2007 года"
    files["ru/banned.html"] = page("ru", "Claims", f"<p>{banned}</p>")
    if broken:
        header = '<div class="blue-strip"></div>\n<header id="hdr" data-arena="3d"><a href="/index.html">PCone</a></header>'
        files["en/header.html"] = page("en", "Header", "<p>Top.</p>", header=header)
    else:
        files["en/header.html"] = page("en", "Header", "<p>Top.</p>")
    if broken:
        files["ru/warranty.html"] = page("ru", "Warranty", "<p>Гарантия на работу один месяц.</p>")
    else:
        files["ru/warranty.html"] = page("ru", "Warranty", f"<p>{WARRANTY}</p>")
    free_body = "<p>Проверка бесплатно.</p>" if broken else "<p>Проверка в лаборатории.</p>"
    files["ru/free.html"] = page("ru", "Note", free_body)
    if broken:
        files["fr/asset.html"] = page(
            "fr",
            "Asset",
            "<p>File.</p>",
            extra_head='<link rel="stylesheet" href="/css/missing.css">',
        )
    else:
        files["fr/asset.html"] = page("fr", "Asset", "<p>File.</p>")
    link = '<p><a href="/ru/ghost.html">gone</a></p>' if broken else '<p><a href="/index.html">home</a></p>'
    files["ar/link.html"] = page("ar", "Link", link)
    hreflang = """<link rel="alternate" hreflang="he" href="https://pconelab.co.il/lang-only.html">
<link rel="alternate" hreflang="ru" href="https://pconelab.co.il/ru/lang-only.html">"""
    files["lang-only.html"] = page("he", "Lang", "<p>One language.</p>", extra_head=hreflang)
    if not broken:
        files["ru/lang-only.html"] = page(
            "ru",
            "Lang ru",
            "<p>Second language.</p>",
            extra_head="""<link rel="alternate" hreflang="he" href="https://pconelab.co.il/lang-only.html">
<link rel="alternate" hreflang="ru" href="https://pconelab.co.il/ru/lang-only.html">""",
        )
    about_links = """<link rel="alternate" hreflang="he" href="https://pconelab.co.il/about.html">
<link rel="alternate" hreflang="ru" href="https://pconelab.co.il/ru/about.html">"""
    if not broken:
        about_links += '\n<link rel="alternate" hreflang="en" href="https://pconelab.co.il/en/about.html">'
    files["about.html"] = page("he", "About", "<p>About the lab.</p>", extra_head=about_links)
    files["ru/about.html"] = page("ru", "About ru", "<p>About.</p>")
    files["en/about.html"] = page("en", "About en", "<p>About.</p>")
    css = "/css/plain.css" if broken else "/css/base-a1b2c3d4.css"
    files["cache.html"] = page("en", "Cache", "<p>Style.</p>", css=css)
    if broken:
        files["jsonld.html"] = page("en", "JSON", "<p>Data.</p>", extra_head='<script type="application/ld+json">{</script>')
    else:
        files["jsonld.html"] = page(
            "en",
            "JSON",
            "<p>Data.</p>",
            extra_head='<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebPage","name":"PCone"}</script>',
        )
    for rel, html in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
    locs = [url_for(rel) for rel in files]
    if broken:
        locs.append(BASE + "/missing-page.html")
    body = ["<?xml version='1.0' encoding='UTF-8'?>", "<urlset>"]
    for loc in locs:
        body.append(f"<url><loc>{loc}</loc></url>")
    body.append("</urlset>")
    (dest / "sitemap.xml").write_text("\n".join(body) + "\n", encoding="utf-8")


def url_for(rel: str) -> str:
    if rel == "index.html":
        return BASE + "/"
    return BASE + "/" + rel


def main() -> None:
    write_tree(ROOT / "broken", True)
    write_tree(ROOT / "fixed", False)
    expected = {
        "findings": [
            {"rule_id": "HOURS_TEXT", "url": BASE + "/ru/hours.html"},
            {"rule_id": "HOURS_JSONLD", "url": BASE + "/ru/hours-json.html"},
            {"rule_id": "CONTACT", "url": BASE + "/en/contact.html"},
            {"rule_id": "META_PRICE", "url": BASE + "/en/meta.html"},
            {"rule_id": "PRICE_FACT", "url": BASE + "/ru/price.html"},
            {"rule_id": "BANNED_CLAIM", "url": BASE + "/ru/banned.html"},
            {"rule_id": "OLD_HEADER", "url": BASE + "/en/header.html"},
            {"rule_id": "WARRANTY_RU", "url": BASE + "/ru/warranty.html"},
            {"rule_id": "FREE_CLAIM", "url": BASE + "/ru/free.html"},
            {"rule_id": "ASSET_404", "url": BASE + "/fr/asset.html"},
            {"rule_id": "LINK_BROKEN", "url": BASE + "/ar/link.html"},
            {"rule_id": "LANG_404", "url": BASE + "/lang-only.html"},
            {"rule_id": "HREFLANG", "url": BASE + "/about.html"},
            {"rule_id": "CACHE_BUST", "url": BASE + "/cache.html"},
            {"rule_id": "JSONLD", "url": BASE + "/jsonld.html"},
            {"rule_id": "PAGE_4XX", "url": BASE + "/missing-page.html"},
        ]
    }
    Path(__file__).resolve().parent.joinpath("expected.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

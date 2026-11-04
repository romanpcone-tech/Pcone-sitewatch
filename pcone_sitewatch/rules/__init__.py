"""v2 detectors. Markup rules run in preflight; geometry is separate."""

from pcone_sitewatch.rules import (
    asset_404,
    banned_claim,
    cache_bust,
    contact,
    free_claim,
    hours_jsonld,
    hours_text,
    hreflang,
    jsonld,
    lang_404,
    link_broken,
    meta_price,
    old_header,
    page_4xx,
    price_fact,
    warranty_ru,
)

MARKUP = (
    hours_text,
    hours_jsonld,
    contact,
    meta_price,
    price_fact,
    banned_claim,
    old_header,
    warranty_ru,
    free_claim,
    asset_404,
    link_broken,
    lang_404,
    hreflang,
    cache_bust,
    jsonld,
    page_4xx,
)


def check_page(page, canon: dict) -> list:
    found = []
    for module in MARKUP:
        if module is page_4xx:
            continue
        found.extend(module.check(page, canon))
    return found

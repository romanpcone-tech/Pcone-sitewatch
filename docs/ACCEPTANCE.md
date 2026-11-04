# Приёмка v2

Ветка: `cursor/pcone-sitewatch-e5ad`

## pytest -q

```
....................                                                     [100%]
20 passed in 0.76s
```

## preflight

С поломками (код 1):

```
preflight: 16 находок (8 critical) — выкладка запрещена
```

16 строк в `findings.jsonl`, набор совпадает с `tests/expected.json`.

Исправленная копия (код 0):

```
preflight: 0 находок — можно выкладывать
```

## Правила

| Правило | Что ловит | Доказательство | Тест |
|---|---|---|---|
| HOURS_TEXT | видимые часы не по канону, в том числе перерыв с подписью «пн-чт» / «ב׳-ה׳» | `break labelled пн-чт/ב׳-ה׳` | `test_each_rule_positive_and_negative`, `test_hebrew_break_label_is_a_defect`, `test_canon_edit_changes_hours_without_code_edit` |
| HOURS_JSONLD | `openingHoursSpecification` не совпадает с интервалами из канона | `Sunday: 09:00-19:00; Friday: missing` | тот же прогон фикстуры |
| CONTACT | почта, `tel:` или адрес не из канона | `info@pconelab.co.il != ron@pcone.co.il` | `test_contact_wrong_phone` |
| META_PRICE | цена в description/og/twitter, кроме 200 ₪ | `350 ₪` | `test_meta_allows_only_diagnostics_200` |
| PRICE_FACT | цена в тексте против `price_facts` | `diagnostics: 999 ₪ != 200` | фикстура `ru/price.html` |
| BANNED_CLAIM | фразы из `banned` | `срочная диагностика` | `test_footer_used_link_is_not_a_banned_claim` |
| OLD_HEADER | не-Arena `<header>` или элемент `blue-strip` | `blue-strip element <div>` | фикстура `en/header.html` |
| WARRANTY_RU | текст с «Гарантия» не содержит канон дословно | короткая фраза вместо канона | фикстура `ru/warranty.html` |
| FREE_CLAIM | «бесплатно» / free, только `report_only` | `report only: бесплатно` | фикстура `ru/free.html` |
| ASSET_404 | нет файла css/assets/img/js | `missing /css/missing.css` | фикстура |
| LINK_BROKEN | внутренняя ссылка без файла | `missing /ru/ghost.html` | фикстура |
| LANG_404 | цель hreflang без файла | `ru .../ru/lang-only.html` | фикстура |
| HREFLANG | существующий язык не перечислен | нет `en/about.html` в наборе | фикстура |
| CACHE_BUST | css/js без `?v=` и без хеша в имени | `/css/plain.css` | фикстура |
| JSONLD | пустой или невалидный ld+json | `JSON does not parse` | фикстура |
| PAGE_4XX | адрес из sitemap без файла | `missing-page.html` | фикстура |
| MOBILE_OVERFLOW | шапка шире 390 px | без браузера `action=skipped`, это не «чисто» | `test_mobile_overflow_without_browser_is_skipped` |

## canon.json

Читаются ключи: `hours`, `contacts`, `meta.only_allowed_price`, `price_facts`, `banned`, `warranty.ru`, `warranty.severity`, `free_claims.note`, `allowlist_seed`, `severity`.

Заглушка: `old_header` ловится структурно (`header` без `id=hdr`/`data-arena`, либо класс `blue-strip`). Отдельного селектора старой полосы в каноне нет.

## Решения и вопросы

Сделано так: v2 только обнаруживает, `action` не бывает `safe_auto`. `/gta-rp` — путь `report_only` из канона, не строка allowlist. Пять точных URL `article-regional-versions` записаны в allowlist без `*`. Ссылка «Б/у техника» не дефект и читается из `allowlist_seed`.

ТРЕБУЕТ РЕШЕНИЯ ЗАКАЗЧИКА: канон `allowlist_seed` для `/gta-rp/*` задаёт правило `*`, а формат allowlist это запрещает. Сейчас это не строка allowlist, а принудительный `info` / `report_only`.

ТРЕБУЕТ РЕШЕНИЯ ЗАКАЗЧИКА: какой точный HTML-маркер старой синей полосы, если это не класс `blue-strip` и не второй `<header>` без `id="hdr"`?

ТРЕБУЕТ РЕШЕНИЯ ЗАКАЗЧИКА: иврит на живом сайте лежит в корне `/`, а не в `/he/`. Правило языков смотрит на фактические файлы и hreflang.

ТРЕБУЕТ РЕШЕНИЯ ЗАКАЗЧИКА: при 2 запросах в секунду 200 адресов не укладываются в 60 секунд. `fast` по сети берёт не больше 200 HTML и не обещает 60 секунд.

## Время и граница v1

Собрано за эту сессию. За границей v1: автоправка и откат на сервере, магазин WooCommerce, скорость и Search Console, полный обход всех ~4257 URL карты за 30 минут.

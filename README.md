# PCone sitewatch

Сторож живого сайта `https://pconelab.co.il`. Только чтение: находит поломки и пишет отчёт. Сайт он не правит.

Факты (часы, телефон, почта, цены, запрещённые фразы, гарантия) лежат в `sitewatch/canon.json`. Код их не дублирует. Стартовая копия — `docs/canon.seed.json`.

## Одна команда

```bash
python -m pcone_sitewatch preflight --root <копия-сайта> --base https://pconelab.co.il
```

Код `1` — выкладку делать нельзя. Код `0` — критичных и высоких находок нет.

Другие режимы: `fast`, `nightly`, `verify --root <копия> --before <snapshot.json> --pages <файл>`, `watch-silence --state sitewatch/state.json --max-age 26h`, `digest --state sitewatch/state.json`.

## Куда смотреть

- `sitewatch/findings.jsonl` — текущий прогон
- `sitewatch/history/` — прошлые прогоны, 30 дней
- `sitewatch/state.json` — история находок и `published_at`
- `sitewatch/meta.json` — время, число адресов, sha256 канона
- `sitewatch/report.html` — сводка с телефона
- `sitewatch/ALERT.md` — только критичное, падение или молчание
- `sitewatch/SUMMARY.txt` — одна строка digest

## Как Рон закрывает находку

Не через GitHub. На своём сервере он дописывает строку в `https://ron.pcone.co.il/files/sitewatch/closed.txt`:

```text
<id> <YYYY-MM-DD> # комментарий
```

Следующий прогон ставит `closed_by: "ron"`. Если поломки на странице уже нет, статус становится `fixed`.

После выкладки Рон обновляет `published.txt` (одна строка ISO 8601 с часовым поясом). Ночной workflow раз в 30 минут сравнивает её с `state.json` и запускает `fast`, только если время новее.

Исключения «так задумано» — `sitewatch/allowlist.txt`:

```text
rule_id | url | причина | кто, дата
```

Без причины строка не действует. `*` в адресе запрещён, строка игнорируется. Страницы `/gta-rp` (пять языков) в этот файл не входят: в каноне у них правило `*`, формат allowlist его запрещает. Детектор оставляет находки, но ставит `info` и `report_only`. Ссылка подвала «Б/у техника» не дефект: это исключение читается из `allowlist_seed`, а не из строки с маской.

## Переменные

- `python -m pcone_sitewatch` не требует ключей.
- Ночной прогон в GitHub Actions ставит Playwright только для `MOBILE_OVERFLOW`. Без браузера правило `skipped`, это не «чисто».

## Следующие этапы

Магазин WooCommerce, скорость страниц, Search Console, автоправка на сервере Рона.

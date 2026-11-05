"""Phone-friendly HTML report."""

from __future__ import annotations

import html
from datetime import date

from pcone_sitewatch.allowlist import Allow
from pcone_sitewatch.finding import Finding


def render(findings: list[Finding], urls_checked: int, stale_rows: list[Allow] | None = None, show_stale: bool = False) -> str:
    stale_rows = stale_rows or []
    hidden = [item for item in findings if item.allowlist]
    visible = [item for item in findings if not item.allowlist and item.action != "skipped"]
    critical = [item for item in visible if item.severity == "critical"]
    repeated = [item for item in visible if item.repeat or item.shared_count >= 3]
    parts = [
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        "<title>PCone sitewatch</title>",
        "<style>body{font:16px/1.4 sans-serif;margin:16px;background:#111;color:#f5f5f5}",
        "a{color:#9cf} .card{border:1px solid #333;border-radius:12px;padding:12px;margin:12px 0}",
        ".bad{border-color:#a33} h1{font-size:1.4rem}</style></head><body>",
        f"<h1>Найдено {len(visible)}</h1>",
        f"<p>Проверено адресов: {urls_checked}. Критичных: {len(critical)}.</p>",
        f"<p>скрыто по allowlist: {len(hidden)}</p>",
    ]
    by_rule: dict[str, list] = {}
    for item in visible:
        by_rule.setdefault(item.rule_id, []).append(item)
    parts.append("<h2>По правилам</h2><ul>")
    for rule, items in sorted(by_rule.items(), key=lambda kv: -len(kv[1])):
        parts.append(f"<li>{html.escape(rule)}: {len(items)}</li>")
    parts.append("</ul>")
    for rule, items in sorted(by_rule.items(), key=lambda kv: -len(kv[1])):
        parts.append(f"<h2>{html.escape(rule)} — {len(items)}</h2>")
        for item in items[:30]:
            klass = "card bad" if item.severity == "critical" else "card"
            parts.append(
                f"<section class='{klass}'><b>{html.escape(item.severity)} {html.escape(item.rule_id)}</b>"
                f"<div><a href='{html.escape(item.url)}'>{html.escape(item.url)}</a></div>"
                f"<pre>{html.escape(item.evidence)}</pre></section>"
            )
        if len(items) > 30:
            parts.append(f"<p>…и ещё {len(items) - 30} таких же</p>")
    parts.append("<h2>Повторяется: искать в шаблоне</h2>")
    if not repeated:
        parts.append("<p>Нет.</p>")
    grouped: dict[tuple, int] = {}
    for item in repeated:
        where = item.shared_file or (item.shared_urls[0] if item.shared_urls else item.url)
        key = (item.rule_id, where)
        grouped[key] = grouped.get(key, 0) + 1
    for (rule, where), count in sorted(grouped.items(), key=lambda kv: -kv[1])[:40]:
        parts.append(f"<p>{html.escape(rule)}: {html.escape(str(where))} — {count}</p>")
    if len(grouped) > 40:
        parts.append(f"<p>…и ещё {len(grouped) - 40} групп</p>")
    if show_stale:
        parts.append("<h2>проверить, ещё задумано?</h2>")
        if not stale_rows:
            parts.append("<p>Нет исключений старше 60 дней.</p>")
        for row in stale_rows:
            parts.append(
                f"<p>{html.escape(row.rule_id)} {html.escape(row.url)} {html.escape(row.reason)} {html.escape(row.who)}</p>"
            )
    parts.append("</body></html>")
    return "".join(parts)


def digest_line(state: dict) -> str:
    repo = state.get("repo") or "https://github.com/romanpcone-tech/Pcone-sitewatch"
    if state.get("status") == "failed":
        reason = state.get("fail_reason") or "ошибка"
        line = f"Сторож: прогон не прошёл — {reason}"
    elif state.get("geometry") == "skipped" and not state.get("critical_count") and not state.get("new_count"):
        line = f"Сторож: геометрия не проверена (нет браузера) — {repo}"
    elif not state.get("new_count") and not state.get("critical_count"):
        checked = state.get("urls_checked") or 0
        line = f"Сторож: всё чисто (проверено {checked}) — {repo}"
    else:
        hint = state.get("hint") or "сайт"
        line = (
            f"Сторож: {state.get('new_count') or 0} новых, "
            f"{state.get('critical_count') or 0} критичная ({hint}) — {repo}"
        )
    return line[:140]


def sunday(day: date) -> bool:
    return day.weekday() == 6

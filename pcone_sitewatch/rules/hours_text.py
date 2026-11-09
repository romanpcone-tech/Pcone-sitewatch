from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.rules.hourslib import canon_break, read_visible, visible_problem


def top_level(blocks: list[dict]) -> list[dict]:
    """Убирает вложенные копии одной и той же строки часов.

    Виджет расписания отдаёт контейнер со всеми днями и тут же дочерние элементы
    по одному дню. Ребёнок — точная часть текста родителя, поэтому его текст
    целиком входит в уже оставленный блок. Проверять такой огрызок отдельно нельзя:
    в нём заведомо нет остальных дней, и сторож ругался бы на верную страницу.
    """
    kept: list[dict] = []
    for block in sorted(blocks, key=lambda item: len(item["text"]), reverse=True):
        text = block["text"].strip()
        if not text:
            continue
        if any(text in other["text"] for other in kept):
            continue
        kept.append(block)
    return kept


def check(page, canon: dict) -> list[Finding]:
    view = page.parsed()
    blocks = top_level(list(view["hours"]))
    if not blocks:
        start, end = canon_break(canon)
        visible = view["visible"]
        if start in visible and end in visible:
            blocks = [{"text": visible, "line": 0}]
    found = []
    for block in blocks:
        problem = visible_problem(read_visible(block["text"], canon), canon)
        if not problem:
            continue
        found.append(
            Finding(
                rule_id="HOURS_TEXT",
                severity=severity(canon, "wrong hours"),
                url=page.url,
                file=page.rel,
                target="visible",
                evidence=problem + " | " + block["text"][:240],
            )
        )
        break
    return found

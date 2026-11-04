from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.rules.hourslib import canon_break, read_visible, visible_problem


def check(page, canon: dict) -> list[Finding]:
    view = page.parsed()
    blocks = list(view["hours"])
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

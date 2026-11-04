from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding
from pcone_sitewatch.rules.hourslib import jsonld_problem, read_visible, visible_problem


def check(page, canon: dict) -> list[Finding]:
    view = page.parsed()
    problem = jsonld_problem(view["jsonld"], canon)
    if not problem:
        return []
    extra = ""
    if view["hours"]:
        visible = visible_problem(read_visible(view["hours"][0]["text"], canon), canon)
        if visible:
            extra = " | text: " + visible
    return [
        Finding(
            rule_id="HOURS_JSONLD",
            severity=severity(canon, "wrong hours"),
            url=page.url,
            file=page.rel,
            target="openingHours",
            evidence=problem + extra,
        )
    ]

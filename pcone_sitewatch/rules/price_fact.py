"""Body prices are compared only with price_facts in canon.json."""

from __future__ import annotations

import re

from pcone_sitewatch.finding import Finding

_AMOUNT = re.compile(r"(?<!\d)(\d{2,5})(?:\s*[-–—]\s*(\d{2,5}))?\s*₪")


def _prefix(text_ru: str) -> str:
    cut = re.split(r"\d|«", text_ru, maxsplit=1)[0]
    cut = cut.replace("только", " ").replace("цены на", " ")
    cut = re.sub(r"\s+", " ", cut).strip(" —.,")
    return re.sub(r"\s+от$", "", cut).strip()


def check(page, canon: dict) -> list[Finding]:
    visible = page.parsed()["visible"]
    if "₪" not in visible:
        return []
    facts = []
    for fact in canon.get("price_facts") or []:
        prefix = _prefix(fact.get("text_ru") or "")
        if prefix:
            facts.append((len(prefix), prefix.lower(), fact))
    facts.sort(reverse=True)
    found = []
    for match in _AMOUNT.finditer(visible):
        # Метка должна стоять в том же куске текста: берём БЛИЖАЙШУЮ метку перед
        # ценой и отбрасываем её, если между меткой и ценой уже стоит другой «₪».
        # Так «Чистка 350 ₪» не читается как «Диагностика 350 ₪», но при этом
        # «Диагностика (250 ₪)» и «Диагностика. 250 ₪» продолжают ловиться.
        window_start = max(0, match.start() - 60)
        window = visible[window_start : match.end()]
        low = window.lower()
        amount = int(match.group(1))
        amount_hi = int(match.group(2) or match.group(1))
        fact = None
        best_pos = -1
        for _, prefix, item in facts:
            pos = low.rfind(prefix)
            if pos != -1 and pos > best_pos:
                best_pos, fact = pos, item
        if fact is None:
            continue
        between = low[best_pos : len(low) - len(match.group(0))]
        if "₪" in between:
            continue
        kind = fact.get("kind")
        problem = None
        if kind == "exact" and amount != int(fact["amount"]):
            problem = f"{fact['id']}: {amount} ₪ != {fact['amount']}"
        elif kind == "from":
            preceded = bool(re.search(r"(?:от|from)\s*$", visible[max(0, match.start() - 12):match.start()], re.I))
            if amount < int(fact["amount"]) or not preceded:
                problem = f"{fact['id']}: expected from {fact['amount']} ₪"
        elif kind == "range":
            if amount < int(fact["min"]) or amount_hi > int(fact["max"]):
                problem = f"{fact['id']}: {amount} outside {fact['min']}-{fact['max']}"
        elif kind == "from_only":
            preceded = bool(re.search(r"(?:от|from)\s*$", visible[max(0, match.start() - 12):match.start()], re.I))
            if not preceded:
                problem = f"{fact['id']}: price must be «от N ₪»"
        if problem:
            found.append(
                Finding(
                    rule_id="PRICE_FACT",
                    severity="medium",
                    url=page.url,
                    file=page.rel,
                    target=fact["id"],
                    evidence=problem + " | " + window.strip(),
                )
            )
            break
    return found

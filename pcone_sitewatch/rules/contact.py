import re

from pcone_sitewatch.canon import severity
from pcone_sitewatch.finding import Finding

_EMAIL = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,10}\b")


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _same_phone(found: str, canon_phone: str) -> bool:
    got = _digits(found)
    want = _digits(canon_phone)
    if not got or not want:
        return False
    if got == want or got.endswith(want) or want.endswith(got):
        return True
    if want.startswith("0") and got.endswith(want[1:]):
        return True
    return False


def check(page, canon: dict) -> list[Finding]:
    contacts = canon["contacts"]
    view = page.parsed()
    found: list[Finding] = []
    want = str(contacts["email"]).lower()
    emails = {item.lower() for item in view["emails"]}
    emails.update(item.lower() for item in _EMAIL.findall(view["visible"]))
    for email in sorted(emails):
        if email == want:
            continue
        found.append(
            Finding(
                rule_id="CONTACT",
                severity=severity(canon, "wrong email"),
                url=page.url,
                file=page.rel,
                target="email",
                evidence=f"{email} != {contacts['email']}",
            )
        )
        break
    for tel in view["tels"]:
        if _same_phone(tel, contacts["phone"]):
            continue
        found.append(
            Finding(
                rule_id="CONTACT",
                severity=severity(canon, "wrong phone"),
                url=page.url,
                file=page.rel,
                target="phone",
                evidence=f"{tel} != {contacts['phone']}",
            )
        )
        break
    street = (contacts.get("address") or {}).get("street") or ""
    number = street.split()[-1] if street else ""
    visible = view["visible"]
    if street and number and ("Lavon" in visible or "Pinhas" in visible):
        # Точное совпадение — норма. Дальше различаем два разных случая, иначе 642 страницы
        # каталога запчастей получали «medium» просто за адрес без номера дома
        # («Pinhas Lavon St, Netanya» вместо «Pinhas Lavon 18»).
        if street in visible:
            pass
        else:
            other = re.search(r"Lavon[^\n\d]{0,14}(\d{1,3})", visible)
            if other and other.group(1) != number:
                found.append(
                    Finding(
                        rule_id="CONTACT",
                        severity=severity(canon, "wrong address"),
                        url=page.url,
                        file=page.rel,
                        target="address",
                        evidence=f"address is not {street}",
                    )
                )
            else:
                found.append(
                    Finding(
                        rule_id="CONTACT",
                        severity="info",
                        url=page.url,
                        file=page.rel,
                        target="address",
                        evidence=f"address without house number: {street}",
                    )
                )
    return found

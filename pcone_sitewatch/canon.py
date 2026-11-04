"""Load sitewatch/canon.json. Facts stay in that file."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REQUIRED = (
    "hours",
    "contacts",
    "meta",
    "price_facts",
    "banned",
    "warranty",
    "free_claims",
    "allowlist_seed",
    "severity",
)


class CanonError(ValueError):
    pass


def default_path() -> Path:
    return Path(__file__).resolve().parent.parent / "sitewatch" / "canon.json"


def load(path: str | Path | None = None) -> dict:
    file = Path(path) if path else default_path()
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CanonError(f"canon.json missing: {file}") from exc
    except json.JSONDecodeError as exc:
        raise CanonError(f"canon.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CanonError("canon.json must be a JSON object")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise CanonError("canon.json missing keys: " + ", ".join(missing))
    hours = data["hours"]
    for key in ("sun", "mon_thu", "fri", "sat", "break_weekdays", "defect_if_labelled"):
        if key not in hours:
            raise CanonError(f"canon.json hours.{key} missing")
    if "email" not in data["contacts"] or "phone" not in data["contacts"]:
        raise CanonError("canon.json contacts.phone and contacts.email are required")
    if "only_allowed_price" not in data["meta"]:
        raise CanonError("canon.json meta.only_allowed_price missing")
    return data


def sha256(path: str | Path | None = None) -> str:
    file = Path(path) if path else default_path()
    return hashlib.sha256(file.read_bytes()).hexdigest()


def severity(canon: dict, phrase: str) -> str:
    table = canon.get("severity") or {}
    for name in ("critical", "high"):
        items = table.get(name) or []
        if phrase in items:
            return name
    return "medium"

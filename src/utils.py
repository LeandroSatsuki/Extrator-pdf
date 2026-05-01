from __future__ import annotations

from datetime import date, datetime
from typing import Any


def safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def generate_quote_number() -> str:
    return "ORC-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def generate_order_number() -> str:
    return "PED-" + datetime.now().strftime("%Y%m%d-%H%M%S")


def format_date_br(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    text = safe_text(value)
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text).strftime("%d/%m/%Y")
    except ValueError:
        return text


def format_brl(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    formatted = f"{number:,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_weight(value: Any) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:.2f}".replace(".", ",") + " g"


def basic_document_format_is_valid(value: str, *, kind: str) -> bool:
    digits = "".join(char for char in safe_text(value) if char.isdigit())
    if not digits:
        return True
    if kind == "cpf":
        return len(digits) == 11
    if kind == "cnpj":
        return len(digits) == 14
    return False

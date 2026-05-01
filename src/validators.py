from __future__ import annotations

import math
import re
from typing import Any

from .models import COMMON_UNITS


ITEM_LINE_PATTERN = re.compile(
    r"^\d{8,12}\s+.+?\s+\d+,\d{2}\s+\d+\s+[A-ZÇ]{2,3}\s+"
    r"R\$\s?[\d.]+,\d{2}\s+[\d.]+,\d{2}%?\s+"
    r"R\$\s?[\d.]+,\d{2}\s+R\$\s?[\d.]+,\d{2}$"
)


def br_number_to_float(valor: Any) -> float | None:
    if valor is None:
        return None

    text = str(valor).strip()
    if not text:
        return None

    text = text.replace("R$", "").replace("%", "").strip()
    text = text.replace(" ", "")

    if not re.fullmatch(r"-?[\d.]+,\d+", text) and not re.fullmatch(r"-?\d+", text):
        return None

    try:
        return float(text.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def br_money_to_float(valor: Any) -> float | None:
    return br_number_to_float(valor)


def parse_brazilian_decimal(value: Any) -> float | None:
    return br_number_to_float(value)


def parse_positive_int(value: Any) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not re.fullmatch(r"\d+", text):
        return None

    try:
        parsed = int(text)
    except ValueError:
        return None

    return parsed if parsed > 0 else None


def is_recognized_unit(unit: Any) -> bool:
    if unit is None:
        return False
    text = str(unit).strip().upper()
    return text in COMMON_UNITS or bool(re.fullmatch(r"[A-ZÇ]{2,3}", text))


def validar_total(quantity: int | None, unit_value: float | None, total: float | None) -> bool:
    if quantity is None or unit_value is None or total is None:
        return False
    return math.isclose(quantity * unit_value, total, abs_tol=0.02)


def total_matches(quantity: int | None, unit_value: float | None, total: float | None) -> bool:
    return validar_total(quantity, unit_value, total)


def is_item_line(line: str) -> bool:
    return bool(ITEM_LINE_PATTERN.match((line or "").strip()))


def montar_observacoes(item: dict[str, Any]) -> list[str]:
    observations: list[str] = []

    if not item.get("regex_completa"):
        observations.append("Linha extraída parcialmente")

    product = str(item.get("produto") or "")
    if not re.fullmatch(r"\d{8,12}", product):
        observations.append("Código de produto ausente ou inválido")

    peso = item.get("peso_g")
    if not (isinstance(peso, (int, float)) and peso > 0):
        observations.append("Peso inválido")

    quantidade = item.get("quantidade")
    if not (isinstance(quantidade, int) and quantidade > 0):
        observations.append("Quantidade inválida")

    if not is_recognized_unit(item.get("unidade")):
        observations.append("Unidade não reconhecida")

    money_fields = ("valor_base", "percentual", "valor_unitario", "valor_total")
    if not all(isinstance(item.get(field), (int, float)) for field in money_fields):
        observations.append("Formato monetário suspeito")

    if not validar_total(quantidade, item.get("valor_unitario"), item.get("valor_total")):
        observations.append("Valor total não confere com quantidade x valor unitário")

    if not item.get("classificacao"):
        observations.append("Classificação não identificada")

    return list(dict.fromkeys(observations))


def calcular_confianca(item: dict[str, Any]) -> tuple[int, str, str]:
    score = 0

    if item.get("regex_completa"):
        score += 40

    product = str(item.get("produto") or "")
    if re.fullmatch(r"\d{8,12}", product):
        score += 10

    peso = item.get("peso_g")
    if isinstance(peso, (int, float)) and peso > 0:
        score += 10

    quantidade = item.get("quantidade")
    if isinstance(quantidade, int) and quantidade > 0:
        score += 10

    if is_recognized_unit(item.get("unidade")):
        score += 5

    money_fields = ("valor_base", "percentual", "valor_unitario", "valor_total")
    if all(isinstance(item.get(field), (int, float)) for field in money_fields):
        score += 10

    if validar_total(quantidade, item.get("valor_unitario"), item.get("valor_total")):
        score += 10

    if item.get("classificacao"):
        score += 5

    score = max(0, min(100, score))

    if score >= 90:
        return score, "OK", ""

    return score, "CONFERIR", "; ".join(montar_observacoes(item))

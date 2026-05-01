from __future__ import annotations

from typing import Any


PERCENTAGE_KEYS = ("1_3", "4_6", "7_9", "acima_10")


def calculate_price_tiers(base_price: float | int | None, percentages: dict[str, Any]) -> dict[str, float]:
    base = float(base_price or 0)
    return {
        "preco_1_3": round(base * (1 + float(percentages.get("1_3", 0) or 0) / 100), 2),
        "preco_4_6": round(base * (1 + float(percentages.get("4_6", 0) or 0) / 100), 2),
        "preco_7_9": round(base * (1 + float(percentages.get("7_9", 0) or 0) / 100), 2),
        "preco_acima_10": round(base * (1 + float(percentages.get("acima_10", 0) or 0) / 100), 2),
    }


def get_applied_price(quantity: int | float | None, price_tiers: dict[str, Any]) -> float:
    qty = int(quantity or 0)
    if qty <= 3:
        return float(price_tiers.get("preco_1_3", 0) or 0)
    if qty <= 6:
        return float(price_tiers.get("preco_4_6", 0) or 0)
    if qty <= 9:
        return float(price_tiers.get("preco_7_9", 0) or 0)
    return float(price_tiers.get("preco_acima_10", 0) or 0)


def calculate_item_total(quantity: int | float | None, applied_price: float | int | None) -> float:
    return round(int(quantity or 0) * float(applied_price or 0), 2)

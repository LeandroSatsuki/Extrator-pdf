from __future__ import annotations

from typing import Any


MARKUP_KEYS = (
    "acrescimo_avulso",
    "acrescimo_2_a_4",
    "acrescimo_5_a_7",
    "acrescimo_8_a_19",
    "acrescimo_acima_20",
)

METRIC_PRICE_COLUMNS = (
    "preco_avulso",
    "preco_2_a_4",
    "preco_5_a_7",
    "preco_8_a_19",
    "preco_acima_20",
)


def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def calculate_metric_prices(base_cost: float | int | None, markup_percentages: dict[str, Any]) -> dict[str, float]:
    base = _to_float(base_cost)
    return {
        "preco_avulso": round(base * (1 + _to_float(markup_percentages.get("acrescimo_avulso")) / 100), 2),
        "preco_2_a_4": round(base * (1 + _to_float(markup_percentages.get("acrescimo_2_a_4")) / 100), 2),
        "preco_5_a_7": round(base * (1 + _to_float(markup_percentages.get("acrescimo_5_a_7")) / 100), 2),
        "preco_8_a_19": round(base * (1 + _to_float(markup_percentages.get("acrescimo_8_a_19")) / 100), 2),
        "preco_acima_20": round(base * (1 + _to_float(markup_percentages.get("acrescimo_acima_20")) / 100), 2),
    }


def get_metric_by_quantity(quantity: int | float | None) -> str:
    qty = int(quantity or 0)
    if qty <= 1:
        return "Avulso"
    if qty <= 4:
        return "2 a 4"
    if qty <= 7:
        return "5 a 7"
    if qty <= 19:
        return "8 a 19"
    return "Acima de 20"


def get_price_by_quantity(quantity: int | float | None, metric_prices: dict[str, Any]) -> float:
    metric = get_metric_by_quantity(quantity)
    if metric == "Avulso":
        return _to_float(metric_prices.get("preco_avulso"))
    if metric == "2 a 4":
        return _to_float(metric_prices.get("preco_2_a_4"))
    if metric == "5 a 7":
        return _to_float(metric_prices.get("preco_5_a_7"))
    if metric == "8 a 19":
        return _to_float(metric_prices.get("preco_8_a_19"))
    return _to_float(metric_prices.get("preco_acima_20"))


def calculate_item_total(quantity: int | float | None, applied_price: float | int | None) -> float:
    return round(int(quantity or 0) * float(applied_price or 0), 2)


def markup_sequence_has_warning(markup_percentages: dict[str, Any]) -> bool:
    values = [_to_float(markup_percentages.get(key)) for key in MARKUP_KEYS]
    return any(current > previous for previous, current in zip(values, values[1:]))


def calculate_price_tiers(base_price: float | int | None, percentages: dict[str, Any]) -> dict[str, float]:
    return calculate_metric_prices(base_price, percentages)


def get_applied_price(quantity: int | float | None, price_tiers: dict[str, Any]) -> float:
    return get_price_by_quantity(quantity, price_tiers)

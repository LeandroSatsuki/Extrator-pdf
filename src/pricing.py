from __future__ import annotations

from typing import Any


MARKUP_KEYS = (
    "acrescimo_avulso",
    "acrescimo_3_pecas",
    "acrescimo_5_pecas",
    "acrescimo_10_pecas",
    "acrescimo_20_pecas_alto_atacado",
)

METRIC_PRICE_COLUMNS = (
    "preco_avulso",
    "preco_3_pecas",
    "preco_5_pecas",
    "preco_10_pecas",
    "preco_20_pecas_alto_atacado",
)

METRIC_KEYS_TO_LABELS = {
    "avulso": "Avulso",
    "3_pecas": "3 peças",
    "5_pecas": "5 peças",
    "10_pecas": "10 peças",
    "20_pecas_alto_atacado": "20 peças (alto atacado)",
}

METRIC_KEYS_TO_PRICE_COLUMNS = {
    "avulso": "preco_avulso",
    "3_pecas": "preco_3_pecas",
    "5_pecas": "preco_5_pecas",
    "10_pecas": "preco_10_pecas",
    "20_pecas_alto_atacado": "preco_20_pecas_alto_atacado",
}

LEGACY_MARKUP_KEYS = {
    "acrescimo_3_pecas": ("acrescimo_2_a_4", "4_6"),
    "acrescimo_5_pecas": ("acrescimo_5_a_7", "7_9"),
    "acrescimo_10_pecas": ("acrescimo_8_a_19", "acima_10"),
    "acrescimo_20_pecas_alto_atacado": ("acrescimo_acima_20",),
}

LEGACY_PRICE_COLUMNS = {
    "preco_3_pecas": "preco_2_a_4",
    "preco_5_pecas": "preco_5_a_7",
    "preco_10_pecas": "preco_8_a_19",
    "preco_20_pecas_alto_atacado": "preco_acima_20",
}


def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _markup_value(markup_percentages: dict[str, Any], key: str) -> float:
    if key in markup_percentages:
        return _to_float(markup_percentages.get(key))
    for legacy_key in LEGACY_MARKUP_KEYS.get(key, ()):
        if legacy_key in markup_percentages:
            return _to_float(markup_percentages.get(legacy_key))
    return 0.0


def calculate_metric_prices(base_cost: float | int | None, markup_percentages: dict[str, Any]) -> dict[str, float]:
    base = _to_float(base_cost)
    return {
        "preco_avulso": round(base * (1 + _markup_value(markup_percentages, "acrescimo_avulso") / 100), 2),
        "preco_3_pecas": round(base * (1 + _markup_value(markup_percentages, "acrescimo_3_pecas") / 100), 2),
        "preco_5_pecas": round(base * (1 + _markup_value(markup_percentages, "acrescimo_5_pecas") / 100), 2),
        "preco_10_pecas": round(base * (1 + _markup_value(markup_percentages, "acrescimo_10_pecas") / 100), 2),
        "preco_20_pecas_alto_atacado": round(base * (1 + _markup_value(markup_percentages, "acrescimo_20_pecas_alto_atacado") / 100), 2),
    }


def get_metric_by_total_quantity(total_quantity: int | float | None) -> str:
    qty = int(total_quantity or 0)
    if qty <= 2:
        return "avulso"
    if qty <= 4:
        return "3_pecas"
    if qty <= 9:
        return "5_pecas"
    if qty <= 19:
        return "10_pecas"
    return "20_pecas_alto_atacado"


def get_metric_label(metric_key: str | None) -> str:
    return METRIC_KEYS_TO_LABELS.get(str(metric_key or ""), "")


def get_discount_metric_label(metric_key: str | None) -> str:
    label = get_metric_label(metric_key)
    if label.startswith("20 peças"):
        return "20 peças"
    return label


def get_price_by_metric(metric_prices: dict[str, Any], metric_key: str | None) -> float:
    column = METRIC_KEYS_TO_PRICE_COLUMNS.get(str(metric_key or ""))
    if not column:
        return 0.0
    value = metric_prices.get(column)
    if value in (None, ""):
        value = metric_prices.get(LEGACY_PRICE_COLUMNS.get(column, ""))
    return _to_float(value)


def get_metric_by_quantity(quantity: int | float | None) -> str:
    return get_metric_label(get_metric_by_total_quantity(quantity))


def get_price_by_quantity(quantity: int | float | None, metric_prices: dict[str, Any]) -> float:
    return get_price_by_metric(metric_prices, get_metric_by_total_quantity(quantity))


def calculate_item_total(quantity: int | float | None, applied_price: float | int | None) -> float:
    return round(int(quantity or 0) * float(applied_price or 0), 2)


def markup_sequence_has_warning(markup_percentages: dict[str, Any]) -> bool:
    values = [_to_float(markup_percentages.get(key)) for key in MARKUP_KEYS]
    return any(current > previous for previous, current in zip(values, values[1:]))


def calculate_price_tiers(base_price: float | int | None, percentages: dict[str, Any]) -> dict[str, float]:
    return calculate_metric_prices(base_price, percentages)


def get_applied_price(quantity: int | float | None, price_tiers: dict[str, Any]) -> float:
    return get_price_by_quantity(quantity, price_tiers)

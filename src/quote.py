from __future__ import annotations

from typing import Any

import pandas as pd

from .pricing import calculate_metric_prices
from .utils import basic_document_format_is_valid, safe_text


def _base_cost(product_or_item: dict[str, Any]) -> float:
    value = product_or_item.get("valor_custo_base")
    if value not in (None, ""):
        return float(value or 0)
    unit_value = product_or_item.get("valor_unitario_original")
    if unit_value not in (None, ""):
        return float(unit_value or 0)
    return float(product_or_item.get("valor_base_original") or 0)


def create_quote_item(product: dict[str, Any], percentages: dict[str, Any], quantity: int | None = None) -> dict[str, Any]:
    base_cost = _base_cost(product)
    metric_prices = calculate_metric_prices(base_cost, percentages)
    return {
        "selecionar": True,
        "produto": product.get("produto", ""),
        "descricao": product.get("descricao", ""),
        "peso_g": product.get("peso_g", ""),
        "unidade": product.get("unidade", ""),
        "classificacao": product.get("classificacao", ""),
        "valor_custo_base": base_cost,
        **metric_prices,
        "observacao": product.get("observacao", ""),
        "valor_unitario_original": product.get("valor_unitario_original", 0),
        "valor_base_original": product.get("valor_base_original", 0),
    }


def recalculate_quote_items(items: list[dict[str, Any]], percentages: dict[str, Any]) -> list[dict[str, Any]]:
    recalculated = []
    for item in items:
        updated = dict(item)
        base_cost = _base_cost(updated)
        updated["valor_custo_base"] = base_cost
        updated.update(calculate_metric_prices(base_cost, percentages))
        recalculated.append(updated)
    return recalculated


def calculate_quote_totals(items: list[dict[str, Any]]) -> dict[str, float | int]:
    selected = [item for item in items if item.get("selecionar", True)]
    return {
        "total_modelos": len(selected),
        "quantidade_total": len(selected),
        "valor_total": 0.0,
    }


def validate_quote(
    customer_data: dict[str, Any],
    company_data: dict[str, Any],
    items: list[dict[str, Any]],
    percentages: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    if not safe_text(customer_data.get("nome")):
        errors.append("Informe o nome do cliente.")

    if not basic_document_format_is_valid(customer_data.get("cpf", ""), kind="cpf"):
        errors.append("CPF do cliente com formato inválido. Use 11 dígitos.")

    if not basic_document_format_is_valid(customer_data.get("cnpj", ""), kind="cnpj"):
        errors.append("CNPJ do cliente com formato inválido. Use 14 dígitos.")

    if not safe_text(company_data.get("nome_empresa")):
        errors.append("Informe o nome da empresa.")

    if not safe_text(company_data.get("telefone")) and not safe_text(company_data.get("email")):
        errors.append("Informe telefone ou email da empresa/vendedor.")

    if not safe_text(company_data.get("nome_vendedor")):
        errors.append("Informe o nome do vendedor.")

    selected_items = [item for item in items if item.get("selecionar", True)]
    if not selected_items:
        errors.append("Adicione pelo menos 1 item ao orçamento.")

    for key, label in {
        "acrescimo_avulso": "Acréscimo Avulso",
        "acrescimo_2_a_4": "Acréscimo 2 a 4",
        "acrescimo_5_a_7": "Acréscimo 5 a 7",
        "acrescimo_8_a_19": "Acréscimo 8 a 19",
        "acrescimo_acima_20": "Acréscimo Acima de 20",
    }.items():
        if percentages.get(key) is None:
            errors.append(f"Preencha o campo {label}.")

    return errors


def quote_items_to_dataframe(items: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(items)

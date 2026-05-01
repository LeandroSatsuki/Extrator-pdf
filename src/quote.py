from __future__ import annotations

from typing import Any

import pandas as pd

from .pricing import calculate_item_total, calculate_price_tiers, get_applied_price
from .utils import basic_document_format_is_valid, safe_text


def create_quote_item(product: dict[str, Any], quantity: int, percentages: dict[str, Any]) -> dict[str, Any]:
    tiers = calculate_price_tiers(product.get("valor_unitario_original"), percentages)
    applied_price = get_applied_price(quantity, tiers)
    return {
        "selecionar": True,
        "produto": product.get("produto", ""),
        "descricao": product.get("descricao", ""),
        "peso_g": product.get("peso_g", ""),
        "unidade": product.get("unidade", ""),
        "classificacao": product.get("classificacao", ""),
        "quantidade": int(quantity),
        **tiers,
        "preco_aplicado": applied_price,
        "valor_total": calculate_item_total(quantity, applied_price),
        "observacao": product.get("observacao", ""),
        "valor_unitario_original": product.get("valor_unitario_original", 0),
        "valor_base_original": product.get("valor_base_original", 0),
    }


def recalculate_quote_items(items: list[dict[str, Any]], percentages: dict[str, Any]) -> list[dict[str, Any]]:
    recalculated = []
    for item in items:
        quantity = int(item.get("quantidade") or 0)
        tiers = calculate_price_tiers(item.get("valor_unitario_original"), percentages)
        applied_price = get_applied_price(quantity, tiers)
        updated = dict(item)
        updated.update(tiers)
        updated["preco_aplicado"] = applied_price
        updated["valor_total"] = calculate_item_total(quantity, applied_price)
        recalculated.append(updated)
    return recalculated


def calculate_quote_totals(items: list[dict[str, Any]]) -> dict[str, float | int]:
    selected = [item for item in items if item.get("selecionar", True)]
    return {
        "quantidade_total": int(sum(int(item.get("quantidade") or 0) for item in selected)),
        "valor_total": round(sum(float(item.get("valor_total") or 0) for item in selected), 2),
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

    if not items:
        errors.append("Adicione pelo menos 1 item ao orçamento.")

    for key, label in {
        "1_3": "Acréscimo 1 a 3 unidades",
        "4_6": "Acréscimo 4 a 6 unidades",
        "7_9": "Acréscimo 7 a 9 unidades",
        "acima_10": "Acréscimo acima de 10 unidades",
    }.items():
        if percentages.get(key) is None:
            errors.append(f"Preencha o campo {label}.")

    invalid_quantities = [item for item in items if int(item.get("quantidade") or 0) <= 0]
    if invalid_quantities:
        errors.append("Todos os itens do orçamento devem ter quantidade maior que zero.")

    return errors


def quote_items_to_dataframe(items: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(items)

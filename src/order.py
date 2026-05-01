from __future__ import annotations

from typing import Any

from .pricing import calculate_item_total, get_metric_by_quantity, get_price_by_quantity


def create_order_from_quote(quote: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "selecionar": bool(item.get("selecionar", True)),
            "produto": item.get("produto", ""),
            "descricao": item.get("descricao", ""),
            "quantidade": 1,
            "unidade": item.get("unidade", ""),
            "metrica_aplicada": "Avulso",
            "preco_unitario": item.get("preco_avulso", 0),
            "valor_total": item.get("preco_avulso", 0),
            "observacao": item.get("observacao", ""),
            "valor_custo_base": item.get("valor_custo_base", 0),
            "valor_unitario_original": item.get("valor_unitario_original", 0),
            "valor_base_original": item.get("valor_base_original", 0),
            "preco_avulso": item.get("preco_avulso", 0),
            "preco_2_a_4": item.get("preco_2_a_4", 0),
            "preco_5_a_7": item.get("preco_5_a_7", 0),
            "preco_8_a_19": item.get("preco_8_a_19", 0),
            "preco_acima_20": item.get("preco_acima_20", 0),
        }
        for item in quote.get("items", [])
    ]


def recalculate_order_items(items: list[dict[str, Any]], percentages: dict[str, Any]) -> list[dict[str, Any]]:
    recalculated = []
    for item in items:
        quantity = int(item.get("quantidade") or 0)
        applied_price = get_price_by_quantity(quantity, item)
        updated = dict(item)
        updated["metrica_aplicada"] = get_metric_by_quantity(quantity)
        updated["preco_unitario"] = applied_price
        updated["valor_total"] = calculate_item_total(quantity, applied_price)
        recalculated.append(updated)
    return recalculated


def calculate_order_totals(items: list[dict[str, Any]]) -> dict[str, float | int]:
    selected = [item for item in items if item.get("selecionar")]
    return {
        "quantidade_total": int(sum(int(item.get("quantidade") or 0) for item in selected)),
        "valor_total": round(sum(float(item.get("valor_total") or 0) for item in selected), 2),
    }


def validate_order(order: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not order.get("quote"):
        errors.append("Confirme um orçamento antes de gerar o pedido.")

    selected = [item for item in order.get("items", []) if item.get("selecionar")]
    if not selected:
        errors.append("Selecione pelo menos 1 item para o pedido.")

    if any(int(item.get("quantidade") or 0) <= 0 for item in selected):
        errors.append("A quantidade de cada item selecionado deve ser maior que zero.")

    quote = order.get("quote") or {}
    customer_data = quote.get("customer_data") or {}
    company_data = quote.get("company_data") or {}
    if not customer_data.get("nome"):
        errors.append("Dados do cliente ausentes.")
    if not company_data.get("nome_empresa"):
        errors.append("Dados da empresa ausentes.")

    return errors

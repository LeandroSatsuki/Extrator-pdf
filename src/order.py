from __future__ import annotations

from typing import Any

from .pricing import calculate_item_total, calculate_price_tiers, get_applied_price


def create_order_from_quote(quote: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "selecionar": bool(item.get("selecionar", True)),
            "produto": item.get("produto", ""),
            "descricao": item.get("descricao", ""),
            "quantidade_orcamento": int(item.get("quantidade") or 0),
            "quantidade_pedido": int(item.get("quantidade") or 0),
            "unidade": item.get("unidade", ""),
            "preco_aplicado": item.get("preco_aplicado", 0),
            "valor_total": item.get("valor_total", 0),
            "observacao": item.get("observacao", ""),
            "valor_unitario_original": item.get("valor_unitario_original", 0),
        }
        for item in quote.get("items", [])
    ]


def recalculate_order_items(items: list[dict[str, Any]], percentages: dict[str, Any]) -> list[dict[str, Any]]:
    recalculated = []
    for item in items:
        quantity = int(item.get("quantidade_pedido") or 0)
        tiers = calculate_price_tiers(item.get("valor_unitario_original"), percentages)
        applied_price = get_applied_price(quantity, tiers)
        updated = dict(item)
        updated["preco_aplicado"] = applied_price
        updated["valor_total"] = calculate_item_total(quantity, applied_price)
        recalculated.append(updated)
    return recalculated


def calculate_order_totals(items: list[dict[str, Any]]) -> dict[str, float | int]:
    selected = [item for item in items if item.get("selecionar")]
    return {
        "quantidade_total": int(sum(int(item.get("quantidade_pedido") or 0) for item in selected)),
        "valor_total": round(sum(float(item.get("valor_total") or 0) for item in selected), 2),
    }


def validate_order(order: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not order.get("quote"):
        errors.append("Confirme um orçamento antes de gerar o pedido.")

    selected = [item for item in order.get("items", []) if item.get("selecionar")]
    if not selected:
        errors.append("Selecione pelo menos 1 item para o pedido.")

    if any(int(item.get("quantidade_pedido") or 0) <= 0 for item in selected):
        errors.append("A quantidade de cada item selecionado deve ser maior que zero.")

    quote = order.get("quote") or {}
    customer_data = quote.get("customer_data") or {}
    company_data = quote.get("company_data") or {}
    if not customer_data.get("nome"):
        errors.append("Dados do cliente ausentes.")
    if not company_data.get("nome_empresa"):
        errors.append("Dados da empresa ausentes.")

    return errors

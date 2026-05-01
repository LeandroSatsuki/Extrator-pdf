from __future__ import annotations

import re
from typing import Any

import pandas as pd


PRODUCT_COLUMNS = [
    "produto",
    "descricao",
    "peso_g",
    "unidade",
    "classificacao",
    "valor_grama_classificacao",
    "valor_unitario_original",
    "valor_base_original",
    "arquivo_origem",
    "numero_pedido_origem",
    "observacao",
    "tem_divergencia",
]


def _same_value(left: Any, right: Any) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    try:
        return abs(float(left) - float(right)) < 0.0001
    except (TypeError, ValueError):
        pass
    return str(left).strip() == str(right).strip()


def detect_product_conflicts(items_df: pd.DataFrame) -> dict[str, bool]:
    conflicts: dict[str, bool] = {}
    if items_df.empty or "produto" not in items_df.columns:
        return conflicts

    comparable = ["descricao", "peso_g", "valor_unitario", "valor_base"]
    for code, group in items_df.dropna(subset=["produto"]).groupby("produto", dropna=True):
        first = group.iloc[0]
        has_conflict = False
        for _, row in group.iloc[1:].iterrows():
            if any(not _same_value(first.get(column), row.get(column)) for column in comparable):
                has_conflict = True
                break
        conflicts[str(code)] = has_conflict
    return conflicts


def build_product_base(items_df: pd.DataFrame) -> pd.DataFrame:
    if items_df.empty:
        return pd.DataFrame(columns=PRODUCT_COLUMNS)

    valid = items_df.copy()
    valid["produto"] = valid["produto"].astype(str).str.strip()
    valid = valid[valid["produto"].ne("") & valid["valor_unitario"].notna()]
    conflicts = detect_product_conflicts(valid)

    products: list[dict[str, Any]] = []
    for code, group in valid.groupby("produto", sort=True, dropna=True):
        first = group.iloc[0]
        has_conflict = conflicts.get(str(code), False)
        products.append(
            {
                "produto": str(code),
                "descricao": first.get("descricao", ""),
                "peso_g": first.get("peso_g", ""),
                "unidade": first.get("unidade", ""),
                "classificacao": first.get("classificacao", ""),
                "valor_grama_classificacao": first.get("valor_grama_classificacao", ""),
                "valor_unitario_original": first.get("valor_unitario", 0),
                "valor_base_original": first.get("valor_base", 0),
                "arquivo_origem": first.get("arquivo_origem", ""),
                "numero_pedido_origem": first.get("numero_pedido", ""),
                "observacao": "Produto encontrado em mais de um PDF com dados divergentes." if has_conflict else "",
                "tem_divergencia": has_conflict,
            }
        )

    return pd.DataFrame(products, columns=PRODUCT_COLUMNS)


def normalize_product_code(value: Any) -> str:
    return re.sub(r"\D", "", str(value or "").strip())


def find_products_by_code(product_base: pd.DataFrame, search_code: str) -> list[dict[str, Any]]:
    if product_base.empty:
        return []

    normalized = normalize_product_code(search_code)
    if not normalized:
        return []

    product_codes = product_base["produto"].astype(str).map(normalize_product_code)
    matches = product_base[product_codes.eq(normalized)]
    if matches.empty and len(normalized) == 5:
        matches = product_base[product_codes.str.endswith(normalized, na=False)]

    if matches.empty:
        return []

    return matches.to_dict("records")


def find_product_by_code(product_base: pd.DataFrame, code: str) -> dict[str, Any] | None:
    matches = find_products_by_code(product_base, code)
    if len(matches) != 1:
        return None
    return matches[0]

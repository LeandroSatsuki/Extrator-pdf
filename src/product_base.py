from __future__ import annotations

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


def find_product_by_code(product_base: pd.DataFrame, code: str) -> dict[str, Any] | None:
    if product_base.empty:
        return None

    normalized = str(code or "").strip()
    matches = product_base[product_base["produto"].astype(str).str.strip().eq(normalized)]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .utils import get_data_dir


def _get_last_header_file() -> Path:
    return get_data_dir() / "last_header_data.json"


COMPANY_TO_JSON = {
    "nome_empresa": "company_name",
    "cnpj_empresa": "company_cnpj",
    "endereco_empresa": "company_address",
    "cidade_uf_empresa": "company_city_uf",
    "telefone": "company_phone",
    "whatsapp": "company_whatsapp",
    "email": "company_email",
    "instagram": "company_instagram",
    "nome_vendedor": "seller_name",
}

COMMERCIAL_TO_JSON = {
    "forma_pagamento": "payment_method",
    "prazo_entrega": "delivery_time",
    "validade_dias": "quote_validity_days",
    "observacoes_gerais": "general_notes",
}


def get_default_company_data() -> dict[str, Any]:
    return {
        "nome_empresa": "",
        "cnpj_empresa": "",
        "endereco_empresa": "",
        "cidade_uf_empresa": "",
        "telefone": "",
        "whatsapp": "",
        "email": "",
        "instagram": "",
        "nome_vendedor": "",
    }


def get_default_commercial_data() -> dict[str, Any]:
    return {
        "forma_pagamento": "",
        "prazo_entrega": "",
        "validade_dias": 7,
        "observacoes_gerais": "",
    }


def get_empty_customer_data() -> dict[str, Any]:
    return {
        "nome": "",
        "cpf": "",
        "cnpj": "",
        "telefone": "",
        "email": "",
        "endereco": "",
        "cidade": "",
        "uf": "",
        "observacoes": "",
    }


def load_last_header_data() -> dict[str, dict[str, Any]]:
    defaults = {
        "company_data": get_default_company_data(),
        "commercial_data": get_default_commercial_data(),
    }

    last_header_file = _get_last_header_file()
    if not last_header_file.exists():
        return defaults

    try:
        raw = json.loads(last_header_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return defaults

    company_raw = raw.get("company_data") if isinstance(raw, dict) else {}
    commercial_raw = raw.get("commercial_data") if isinstance(raw, dict) else {}
    if not isinstance(company_raw, dict):
        company_raw = {}
    if not isinstance(commercial_raw, dict):
        commercial_raw = {}

    company_data = get_default_company_data()
    commercial_data = get_default_commercial_data()

    for internal_key, json_key in COMPANY_TO_JSON.items():
        company_data[internal_key] = company_raw.get(json_key, "")

    for internal_key, json_key in COMMERCIAL_TO_JSON.items():
        commercial_data[internal_key] = commercial_raw.get(json_key, "" if internal_key != "validade_dias" else 7)

    try:
        commercial_data["validade_dias"] = int(commercial_data.get("validade_dias") or 7)
    except (TypeError, ValueError):
        commercial_data["validade_dias"] = 7

    return {"company_data": company_data, "commercial_data": commercial_data}


def save_last_header_data(company_data: dict[str, Any], commercial_data: dict[str, Any]) -> bool:
    payload = {
        "company_data": {
            json_key: str(company_data.get(internal_key, "") or "")
            for internal_key, json_key in COMPANY_TO_JSON.items()
        },
        "commercial_data": {
            json_key: commercial_data.get(internal_key, "") or ""
            for internal_key, json_key in COMMERCIAL_TO_JSON.items()
        },
    }

    try:
        last_header_file = _get_last_header_file()
        last_header_file.parent.mkdir(parents=True, exist_ok=True)
        last_header_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return False

    return True

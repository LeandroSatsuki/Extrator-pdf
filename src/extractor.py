from __future__ import annotations

import re
from io import BytesIO
from typing import BinaryIO, Any

import pdfplumber

from .models import IGNORED_PREFIXES, ITEM_COLUMNS
from .validators import calcular_confianca, parse_brazilian_decimal, parse_positive_int


ITEM_RE = re.compile(
    r"^(?P<produto>\d{8,12})\s+"
    r"(?P<descricao>.+?)\s+"
    r"(?P<peso>\d+,\d{2})\s+"
    r"(?P<quantidade>\d+)\s+"
    r"(?P<unidade>[A-ZÇ]{2,3})\s+"
    r"R\$\s?(?P<valor_base>[\d.]+,\d{2})\s+"
    r"(?P<percentual>[\d.]+,\d{2})%?\s+"
    r"R\$\s?(?P<valor_unitario>[\d.]+,\d{2})\s+"
    r"R\$\s?(?P<valor_total>[\d.]+,\d{2})$"
)

PARTIAL_PRODUCT_RE = re.compile(r"^(?P<produto>\d{8,12})\s+(?P<resto>.+)$")
CLASSIFICATION_RE = re.compile(
    r"Classifica(?:ç|c)[aã]o:\s*([A-Z0-9]+)\s+Valor\s+Grama:\s*([\d.,]+)",
    re.IGNORECASE,
)


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip()


def _ascii_upper(text: str) -> str:
    translation = str.maketrans("ÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ", "AAAAEEEIIIOOOOUUUC")
    return text.upper().translate(translation)


def _is_ignored_line(line: str) -> bool:
    upper = _ascii_upper(line)
    return any(upper.startswith(prefix) for prefix in IGNORED_PREFIXES)


def _extract_between(text: str, start: str, end: str) -> str:
    match = re.search(start + r"\s*(.*?)\s*" + end, text, re.IGNORECASE | re.DOTALL)
    return _clean_header_value(match.group(1)) if match else ""


def _extract_until(text: str, start: str, stop_labels: list[str]) -> str:
    stop_pattern = "|".join(stop_labels)
    match = re.search(
        start + r"\s*(.*?)(?=\s+(?:" + stop_pattern + r")\s*:|\s+Foto Produto|\s+Classifica|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    return _clean_header_value(match.group(1)) if match else ""


def _line_value_after_label(full_text: str, label: str, stop_labels: list[str] | None = None) -> str:
    label_pattern = re.escape(label)
    stop_labels = stop_labels or []
    stop_pattern = "|".join(re.escape(stop_label) for stop_label in stop_labels)

    for raw_line in full_text.splitlines():
        line = _normalize_line(raw_line)
        match = re.search(label_pattern + r"\s*(.*)$", line, re.IGNORECASE)
        if not match:
            continue

        value = match.group(1)
        if stop_pattern:
            value = re.split(r"\s+(?:" + stop_pattern + r")\s*:", value, maxsplit=1, flags=re.IGNORECASE)[0]
        return _clean_header_value(value)

    return ""


def _clean_header_value(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" :-")


def _extract_header(full_text: str) -> dict[str, str]:
    flat_text = _clean_header_value(full_text)

    numero = re.search(r"N[úu]mero:\s*(\d+)", flat_text, re.IGNORECASE)
    faturamento = re.search(r"Faturamento:\s*(\d{2}/\d{2}/\d{4})", flat_text, re.IGNORECASE)

    return {
        "numero_pedido": numero.group(1) if numero else "",
        "faturamento": faturamento.group(1) if faturamento else "",
        "cliente": _extract_between(flat_text, r"Cliente:", r"CPF/CNPJ:"),
        "cpf_cnpj": _line_value_after_label(
            full_text,
            "CPF/CNPJ:",
            ["Endereço", "Endereco", "Bairro", "Município", "Municipio", "CEP", "Vendedor", "Tipo.Pag.", "Cond.Pag."],
        ),
        "vendedor": _extract_between(flat_text, r"Vendedor:", r"Tipo\.Pag\.:"),
        "tipo_pagamento": _line_value_after_label(full_text, "Tipo.Pag.:", ["Cond.Pag.", "Frete"]),
        "condicao_pagamento": _line_value_after_label(full_text, "Cond.Pag.:", ["Foto Produto", "Classificação", "Classificacao"]),
    }


def _extract_footer_items_count(full_text: str) -> int | None:
    matches = re.findall(r"Itens:\s*(\d+)", full_text, re.IGNORECASE)
    if not matches:
        return None
    return int(matches[-1])


def _build_item(
    *,
    filename: str,
    header: dict[str, str],
    line: str,
    page_number: int,
    classification: str,
    gram_value: float | None,
    match: re.Match[str] | None,
) -> dict[str, Any]:
    item = {column: "" for column in ITEM_COLUMNS}
    item.update(
        {
            "arquivo_origem": filename,
            "numero_pedido": header.get("numero_pedido", ""),
            "faturamento": header.get("faturamento", ""),
            "cliente": header.get("cliente", ""),
            "cpf_cnpj": header.get("cpf_cnpj", ""),
            "vendedor": header.get("vendedor", ""),
            "tipo_pagamento": header.get("tipo_pagamento", ""),
            "condicao_pagamento": header.get("condicao_pagamento", ""),
            "classificacao": classification or "",
            "valor_grama_classificacao": gram_value,
            "pagina": page_number,
            "linha_original": line,
            "regex_completa": bool(match),
        }
    )

    if match:
        groups = match.groupdict()
        item.update(
            {
                "produto": groups["produto"],
                "descricao": _clean_header_value(groups["descricao"]),
                "peso_g": parse_brazilian_decimal(groups["peso"]),
                "quantidade": parse_positive_int(groups["quantidade"]),
                "unidade": groups["unidade"].upper(),
                "valor_base": parse_brazilian_decimal(groups["valor_base"]),
                "percentual": parse_brazilian_decimal(groups["percentual"]),
                "valor_unitario": parse_brazilian_decimal(groups["valor_unitario"]),
                "valor_total": parse_brazilian_decimal(groups["valor_total"]),
            }
        )
    else:
        partial = PARTIAL_PRODUCT_RE.match(line)
        if partial:
            item["produto"] = partial.group("produto")
            item["descricao"] = _clean_header_value(partial.group("resto"))

    confidence, status, observation = calcular_confianca(item)
    item["confianca_extracao"] = confidence
    item["status_conferencia"] = status
    item["observacao"] = observation

    item.pop("regex_completa", None)
    return item


def _extract_text_lines(pdf: pdfplumber.PDF) -> tuple[list[tuple[int, str]], str]:
    lines: list[tuple[int, str]] = []
    pages_text: list[str] = []

    for page_index, page in enumerate(pdf.pages, start=1):
        text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
        if text.strip():
            pages_text.append(text)
            for raw_line in text.splitlines():
                normalized = _normalize_line(raw_line)
                if normalized:
                    lines.append((page_index, normalized))

    return lines, "\n".join(pages_text)


def extract_pdf(file: BinaryIO | bytes, filename: str) -> dict[str, Any]:
    warnings: list[str] = []

    if isinstance(file, bytes):
        stream: BinaryIO = BytesIO(file)
    else:
        file.seek(0)
        stream = file

    try:
        with pdfplumber.open(stream) as pdf:
            lines, full_text = _extract_text_lines(pdf)
    except Exception as exc:
        message = f"Erro ao ler PDF: {exc}"
        return _empty_result(filename, message)

    if not full_text.strip():
        message = "PDF sem texto pesquisável. Possivelmente escaneado. Necessário OCR."
        return _empty_result(filename, message)

    header = _extract_header(full_text)
    expected_items = _extract_footer_items_count(full_text)

    items: list[dict[str, Any]] = []
    current_classification = ""
    current_gram_value: float | None = None
    in_payment_section = False

    for page_number, line in lines:
        if _ascii_upper(line).startswith("FORMA DE PAGAMENTO"):
            in_payment_section = True
            continue

        classification_match = CLASSIFICATION_RE.search(line)
        if classification_match:
            current_classification = classification_match.group(1).strip()
            current_gram_value = parse_brazilian_decimal(classification_match.group(2))
            continue

        if in_payment_section or _is_ignored_line(line):
            continue

        match = ITEM_RE.match(line)
        partial_match = PARTIAL_PRODUCT_RE.match(line)
        if match or partial_match:
            items.append(
                _build_item(
                    filename=filename,
                    header=header,
                    line=line,
                    page_number=page_number,
                    classification=current_classification,
                    gram_value=current_gram_value,
                    match=match,
                )
            )

    summary = _build_summary(filename, header, items, expected_items, warnings)
    return {"items": items, "summary": summary, "warnings": warnings}


def _build_summary(
    filename: str,
    header: dict[str, str],
    items: list[dict[str, Any]],
    expected_items: int | None,
    warnings: list[str],
) -> dict[str, Any]:
    extracted = len(items)
    lines_ok = sum(1 for item in items if item.get("confianca_extracao", 0) >= 90)
    lines_check = extracted - lines_ok

    if expected_items is None:
        status_pdf = "NÃO ENCONTRADO"
        warnings.append(f"{filename}: quantidade de itens do rodapé não encontrada.")
    elif extracted == expected_items:
        status_pdf = "OK"
    else:
        status_pdf = "DIVERGENTE"
        warnings.append(
            f"{filename}: divergência entre linhas extraídas ({extracted}) e Itens do rodapé ({expected_items})."
        )

    return {
        "arquivo_origem": filename,
        "numero_pedido": header.get("numero_pedido", ""),
        "cliente": header.get("cliente", ""),
        "faturamento": header.get("faturamento", ""),
        "linhas_extraidas": extracted,
        "linhas_ok": lines_ok,
        "linhas_conferir": lines_check,
        "itens_rodape": expected_items if expected_items is not None else "",
        "status_pdf": status_pdf,
        "observacoes_pdf": " ".join(warnings),
    }


def _empty_result(filename: str, message: str) -> dict[str, Any]:
    return {
        "items": [],
        "summary": {
            "arquivo_origem": filename,
            "numero_pedido": "",
            "cliente": "",
            "faturamento": "",
            "linhas_extraidas": 0,
            "linhas_ok": 0,
            "linhas_conferir": 0,
            "itens_rodape": "",
            "status_pdf": "ERRO",
            "observacoes_pdf": message,
        },
        "warnings": [f"{filename}: {message}"],
    }

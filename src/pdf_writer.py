from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .utils import format_brl, format_date_br, safe_text


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, fontSize=19, leading=23))
    styles.add(ParagraphStyle(name="RightSmall", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Line", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="CenterSmall", parent=styles["Small"], alignment=TA_CENTER))
    return styles


def _paragraph(text: Any, style) -> Paragraph:
    value = safe_text(text).replace("\n", "<br/>")
    return Paragraph(value or "-", style)


def _logo_flowable(logo_file: bytes | None) -> Image | None:
    if not logo_file:
        return None
    try:
        image = Image(BytesIO(logo_file), width=7.8 * cm, height=3.0 * cm, kind="proportional")
        image.hAlign = "LEFT"
        return image
    except Exception:
        return None


def _horizontal_line() -> Table:
    table = Table([[""]], colWidths=[17.0 * cm], rowHeights=[0.05 * cm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#999999"))]))
    return table


def _header(title: str, number: str, date_value: Any, logo_file: bytes | None) -> list[Any]:
    styles = _styles()
    logo = _logo_flowable(logo_file)
    left = logo if logo else _paragraph("", styles["Normal"])
    right = [
        _paragraph(f"<b>{title}</b>", styles["TitleCenter"]),
        _paragraph(f"<b>Número:</b> {safe_text(number)}", styles["RightSmall"]),
        _paragraph(f"<b>Data:</b> {format_date_br(date_value)}", styles["RightSmall"]),
    ]
    table = Table([[left, right]], colWidths=[8.6 * cm, 8.4 * cm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return [table, _horizontal_line(), Spacer(1, 0.25 * cm)]


def _line(label: str, value: Any):
    if not safe_text(value):
        return None
    return _paragraph(f"<b>{label}:</b> {safe_text(value)}", _styles()["Line"])


def _append_lines(story: list[Any], rows: list[tuple[str, Any]]) -> None:
    for label, value in rows:
        line = _line(label, value)
        if line is not None:
            story.append(line)


def _company_rows(data: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        ("Empresa", data.get("nome_empresa")),
        ("CNPJ da empresa", data.get("cnpj_empresa")),
        ("Endereço da empresa", data.get("endereco_empresa")),
        ("Cidade/UF da empresa", data.get("cidade_uf_empresa")),
        ("Telefone da empresa", data.get("telefone")),
        ("WhatsApp da empresa", data.get("whatsapp")),
        ("Email da empresa", data.get("email")),
        ("Instagram da empresa", data.get("instagram")),
        ("Site da empresa", data.get("site")),
    ]


def _customer_rows(data: dict[str, Any]) -> list[tuple[str, Any]]:
    document = data.get("cpf") or data.get("cnpj")
    city_state = " / ".join(part for part in [safe_text(data.get("cidade")), safe_text(data.get("uf"))] if part)
    return [
        ("Cliente", data.get("nome")),
        ("CPF/CNPJ do cliente", document),
        ("Telefone do cliente", data.get("telefone")),
        ("Email do cliente", data.get("email")),
        ("Endereço do cliente", data.get("endereco")),
        ("Cidade/UF do cliente", city_state),
        ("Observações do cliente", data.get("observacoes")),
    ]


def _commercial_rows(data: dict[str, Any], *, quote: bool) -> list[tuple[str, Any]]:
    rows = [
        ("Vendedor", data.get("nome_vendedor")),
    ]
    if quote:
        rows.extend(
            [
                ("Data do orçamento", format_date_br(data.get("data_orcamento"))),
                ("Validade do orçamento", f"{data.get('validade_dias')} dias" if safe_text(data.get("validade_dias")) else ""),
            ]
        )
    rows.extend(
        [
            ("Forma de pagamento", data.get("forma_pagamento")),
            ("Prazo de entrega", data.get("prazo_entrega")),
            ("Observações", data.get("observacoes_gerais")),
        ]
    )
    return rows


def _details_block(story: list[Any], company: dict[str, Any], customer: dict[str, Any], *, quote: bool) -> None:
    _append_lines(story, _company_rows(company))
    story.append(Spacer(1, 0.15 * cm))
    _append_lines(story, _customer_rows(customer))
    story.append(Spacer(1, 0.15 * cm))
    _append_lines(story, _commercial_rows(company, quote=quote))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_horizontal_line())
    story.append(Spacer(1, 0.3 * cm))


def _quote_items_table(items: list[dict[str, Any]]) -> Table:
    styles = _styles()
    header = ["Código", "Descrição", "Avulso", "2 a 4", "5 a 7", "8 a 19", "Acima de 20"]
    data = [[_paragraph(column, styles["Small"]) for column in header]]
    for item in items:
        data.append(
            [
                _paragraph(item.get("produto"), styles["Small"]),
                _paragraph(item.get("descricao"), styles["Small"]),
                _paragraph(format_brl(item.get("preco_avulso")), styles["Small"]),
                _paragraph(format_brl(item.get("preco_2_a_4")), styles["Small"]),
                _paragraph(format_brl(item.get("preco_5_a_7")), styles["Small"]),
                _paragraph(format_brl(item.get("preco_8_a_19")), styles["Small"]),
                _paragraph(format_brl(item.get("preco_acima_20")), styles["Small"]),
            ]
        )
    table = Table(data, colWidths=[2.2 * cm, 5.3 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 2.1 * cm], repeatRows=1)
    _style_items_table(table)
    return table


def _order_items_table(items: list[dict[str, Any]]) -> Table:
    styles = _styles()
    header = ["Código", "Descrição", "Qtd.", "Un.", "Métrica", "Preço unit.", "Valor total"]
    data = [[_paragraph(column, styles["Small"]) for column in header]]
    for item in items:
        data.append(
            [
                _paragraph(item.get("produto"), styles["Small"]),
                _paragraph(item.get("descricao"), styles["Small"]),
                _paragraph(item.get("quantidade"), styles["Small"]),
                _paragraph(item.get("unidade"), styles["Small"]),
                _paragraph(item.get("metrica_aplicada"), styles["Small"]),
                _paragraph(format_brl(item.get("preco_unitario")), styles["Small"]),
                _paragraph(format_brl(item.get("valor_total")), styles["Small"]),
            ]
        )
    table = Table(data, colWidths=[2.1 * cm, 5.5 * cm, 1.1 * cm, 1.0 * cm, 2.0 * cm, 2.4 * cm, 2.6 * cm], repeatRows=1)
    _style_items_table(table)
    return table


def _style_items_table(table: Table) -> None:
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )


def _build_document(title: str, number: str, story: list[Any]) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.2 * cm,
        title=f"{title} {number}",
    )
    doc.build(story)
    buffer.seek(0)
    return buffer


def build_quote_pdf(quote_data: dict[str, Any], logo_file: bytes | None = None) -> BytesIO:
    styles = _styles()
    company = quote_data.get("company_data", {})
    customer = quote_data.get("customer_data", {})
    items = [item for item in quote_data.get("items", []) if item.get("selecionar", True)]
    totals = quote_data.get("totals", {})

    story: list[Any] = []
    story.extend(_header("ORÇAMENTO", quote_data.get("numero_orcamento", ""), company.get("data_orcamento"), logo_file))
    _details_block(story, company, customer, quote=True)
    story.append(_quote_items_table(items))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_paragraph(f"<b>Total de modelos orçados:</b> {totals.get('total_modelos', len(items))}", styles["Line"]))
    story.append(
        _paragraph(
            "Observação: Os valores acima são calculados por faixa de quantidade, conforme a métrica selecionada no pedido.",
            styles["Small"],
        )
    )
    story.append(Spacer(1, 0.35 * cm))
    story.append(_paragraph("Este orçamento apresenta valores por faixa de quantidade. O valor final será calculado no pedido conforme a quantidade escolhida.", styles["Small"]))
    return _build_document("ORÇAMENTO", quote_data.get("numero_orcamento", ""), story)


def build_order_pdf(order_data: dict[str, Any], logo_file: bytes | None = None) -> BytesIO:
    styles = _styles()
    quote = order_data.get("quote", {})
    company = quote.get("company_data", {})
    customer = quote.get("customer_data", {})
    items = [item for item in order_data.get("items", []) if item.get("selecionar")]
    totals = order_data.get("totals", {})

    story: list[Any] = []
    story.extend(_header("PEDIDO", order_data.get("numero_pedido", ""), order_data.get("data_pedido"), logo_file))
    story.append(_paragraph(f"<b>Referência do orçamento:</b> {safe_text(quote.get('numero_orcamento'))}", styles["Line"]))
    story.append(Spacer(1, 0.15 * cm))
    _details_block(story, company, customer, quote=False)
    story.append(_order_items_table(items))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_paragraph(f"<b>Quantidade total:</b> {totals.get('quantidade_total', 0)}", styles["Line"]))
    story.append(_paragraph(f"<b>Valor total do pedido:</b> {format_brl(totals.get('valor_total', 0))}", styles["Line"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(_paragraph("<b>Assinatura do cliente:</b> ______________________________________", styles["Line"]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_paragraph("<b>Assinatura do vendedor:</b> ____________________________________", styles["Line"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_paragraph("Pedido gerado a partir do orçamento confirmado.", styles["Small"]))
    return _build_document("PEDIDO", order_data.get("numero_pedido", ""), story)

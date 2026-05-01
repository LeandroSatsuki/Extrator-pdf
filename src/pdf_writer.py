from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .utils import format_brl, format_date_br, safe_text


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, fontSize=18, leading=22))
    styles.add(ParagraphStyle(name="RightSmall", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading3"], fontSize=10, leading=12, spaceAfter=4))
    return styles


def _paragraph(text: Any, style) -> Paragraph:
    value = safe_text(text).replace("\n", "<br/>")
    return Paragraph(value or "-", style)


def _logo_flowable(logo_file: bytes | None) -> Image | None:
    if not logo_file:
        return None
    try:
        image = Image(BytesIO(logo_file), width=6.8 * cm, height=1.6 * cm, kind="proportional")
        image.hAlign = "LEFT"
        return image
    except Exception:
        return None


def _header(title: str, number: str, date_value: Any, logo_file: bytes | None) -> list[Any]:
    styles = _styles()
    logo = _logo_flowable(logo_file)
    left = logo if logo else _paragraph("", styles["Normal"])
    right = [
        _paragraph(f"<b>{title}</b>", styles["TitleCenter"]),
        _paragraph(f"<b>Número:</b> {safe_text(number)}", styles["RightSmall"]),
        _paragraph(f"<b>Data:</b> {format_date_br(date_value)}", styles["RightSmall"]),
    ]
    table = Table([[left, right]], colWidths=[8 * cm, 8.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return [table, Spacer(1, 0.2 * cm)]


def _info_table(title: str, rows: list[tuple[str, Any]]) -> Table:
    styles = _styles()
    data = [[_paragraph(f"<b>{title}</b>", styles["Section"])]]
    data.extend([[_paragraph(f"<b>{label}:</b> {safe_text(value)}", styles["Small"])] for label, value in rows if safe_text(value)])
    table = Table(data, colWidths=[8.1 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F3F3")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _company_rows(data: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        ("Empresa", data.get("nome_empresa")),
        ("CNPJ", data.get("cnpj_empresa")),
        ("Endereço", data.get("endereco_empresa")),
        ("Cidade/UF", data.get("cidade_uf_empresa")),
        ("Telefone", data.get("telefone")),
        ("WhatsApp", data.get("whatsapp")),
        ("Email", data.get("email")),
        ("Instagram", data.get("instagram")),
        ("Site", data.get("site")),
    ]


def _customer_rows(data: dict[str, Any]) -> list[tuple[str, Any]]:
    document = data.get("cpf") or data.get("cnpj")
    return [
        ("Cliente", data.get("nome")),
        ("CPF/CNPJ", document),
        ("Telefone", data.get("telefone")),
        ("Email", data.get("email")),
        ("Endereço", data.get("endereco")),
        ("Cidade/UF", " / ".join(part for part in [safe_text(data.get("cidade")), safe_text(data.get("uf"))] if part)),
        ("Observações", data.get("observacoes")),
    ]


def _commercial_rows(data: dict[str, Any], *, validity: Any = None) -> list[tuple[str, Any]]:
    rows = [
        ("Vendedor", data.get("nome_vendedor")),
        ("Forma de pagamento", data.get("forma_pagamento")),
        ("Prazo de entrega", data.get("prazo_entrega")),
    ]
    if validity is not None:
        rows.insert(1, ("Validade", f"{validity} dias"))
    rows.append(("Observações", data.get("observacoes_gerais")))
    return rows


def _items_table(items: list[dict[str, Any]], *, order: bool = False) -> Table:
    styles = _styles()
    header = ["Código", "Descrição", "Qtd.", "Un.", "Preço unit.", "Valor total"]
    data = [[_paragraph(column, styles["Small"]) for column in header]]
    for item in items:
        quantity = item.get("quantidade_pedido") if order else item.get("quantidade")
        data.append(
            [
                _paragraph(item.get("produto"), styles["Small"]),
                _paragraph(item.get("descricao"), styles["Small"]),
                _paragraph(quantity, styles["Small"]),
                _paragraph(item.get("unidade"), styles["Small"]),
                _paragraph(format_brl(item.get("preco_aplicado")), styles["Small"]),
                _paragraph(format_brl(item.get("valor_total")), styles["Small"]),
            ]
        )

    table = Table(data, colWidths=[2.4 * cm, 6.6 * cm, 1.3 * cm, 1.2 * cm, 2.5 * cm, 2.7 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CCCCCC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _build_document(title: str, number: str, date_value: Any, story: list[Any]) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.2 * cm,
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
    story.append(Table([[_info_table("Dados da empresa", _company_rows(company)), _info_table("Dados do cliente", _customer_rows(customer))]], colWidths=[8.4 * cm, 8.4 * cm]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_info_table("Dados comerciais", _commercial_rows(company, validity=company.get("validade_dias"))))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_items_table(items))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_paragraph(f"<b>Quantidade total de itens:</b> {totals.get('quantidade_total', 0)}", styles["Normal"]))
    story.append(_paragraph(f"<b>Valor total do orçamento:</b> {format_brl(totals.get('valor_total', 0))}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(_paragraph("Este orçamento é válido conforme o prazo informado e está sujeito à disponibilidade dos produtos.", styles["Small"]))
    return _build_document("ORÇAMENTO", quote_data.get("numero_orcamento", ""), company.get("data_orcamento"), story)


def build_order_pdf(order_data: dict[str, Any], logo_file: bytes | None = None) -> BytesIO:
    styles = _styles()
    quote = order_data.get("quote", {})
    company = quote.get("company_data", {})
    customer = quote.get("customer_data", {})
    items = [item for item in order_data.get("items", []) if item.get("selecionar")]
    totals = order_data.get("totals", {})

    story: list[Any] = []
    story.extend(_header("PEDIDO", order_data.get("numero_pedido", ""), order_data.get("data_pedido"), logo_file))
    story.append(_paragraph(f"<b>Referência do orçamento:</b> {safe_text(quote.get('numero_orcamento'))}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Table([[_info_table("Dados da empresa", _company_rows(company)), _info_table("Dados do cliente", _customer_rows(customer))]], colWidths=[8.4 * cm, 8.4 * cm]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_info_table("Dados comerciais", _commercial_rows(company)))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_items_table(items, order=True))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_paragraph(f"<b>Quantidade total:</b> {totals.get('quantidade_total', 0)}", styles["Normal"]))
    story.append(_paragraph(f"<b>Valor total do pedido:</b> {format_brl(totals.get('valor_total', 0))}", styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(_paragraph("<b>Assinatura do cliente:</b> ______________________________________", styles["Normal"]))
    story.append(Spacer(1, 0.25 * cm))
    story.append(_paragraph("<b>Assinatura do vendedor:</b> ____________________________________", styles["Normal"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(_paragraph("Pedido gerado a partir do orçamento confirmado.", styles["Small"]))
    return _build_document("PEDIDO", order_data.get("numero_pedido", ""), order_data.get("data_pedido"), story)

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


DARK = colors.HexColor("#1F1F1F")
MID = colors.HexColor("#777777")
LIGHT_GRID = colors.HexColor("#D9D9D9")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=TA_CENTER, fontSize=19, leading=23))
    styles.add(ParagraphStyle(name="RightSmall", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="Line", parent=styles["Normal"], fontSize=8.5, leading=11))
    styles.add(ParagraphStyle(name="BlockTitle", parent=styles["Small"], fontSize=8.5, leading=11, textColor=colors.white))
    styles.add(ParagraphStyle(name="TableHeader", parent=styles["Small"], fontSize=8, leading=10, textColor=colors.white))
    return styles


def _paragraph(text: Any, style) -> Paragraph:
    value = safe_text(text).replace("\n", "<br/>")
    return Paragraph(value or "", style)


def _kv(label: str, value: Any) -> Paragraph:
    return _paragraph(f"<b>{label}:</b> {safe_text(value)}", _styles()["Line"])


def _join_values(*parts: tuple[str, Any]) -> str:
    rendered = [f"{label}: {safe_text(value)}" for label, value in parts if safe_text(value)]
    return " | ".join(rendered)


def _horizontal_line(color=MID, height: float = 0.04) -> Table:
    table = Table([[""]], colWidths=[17.0 * cm], rowHeights=[height * cm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color)]))
    return table


def draw_logo(logo_file: bytes | None) -> Image | None:
    if not logo_file:
        return None
    try:
        image = Image(BytesIO(logo_file), width=16.2 * cm, height=5.4 * cm, kind="proportional")
        image.hAlign = "LEFT"
        return image
    except Exception:
        return None


def _document_header(title: str, number: str, date_value: Any, logo_file: bytes | None) -> list[Any]:
    styles = _styles()
    story: list[Any] = []
    logo = draw_logo(logo_file)
    if logo:
        story.extend([logo, Spacer(1, 0.12 * cm)])

    title_block = [
        _paragraph(f"<b>{title}</b>", styles["TitleCenter"]),
        _paragraph(f"<b>Número:</b> {safe_text(number)}", styles["RightSmall"]),
        _paragraph(f"<b>Data:</b> {format_date_br(date_value)}", styles["RightSmall"]),
    ]
    table = Table([[title_block]], colWidths=[17.0 * cm])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.extend([table, _horizontal_line(DARK, 0.05), Spacer(1, 0.18 * cm)])
    return story


def _company_cells(company: dict[str, Any]) -> list[Paragraph]:
    return [
        _kv("Empresa", company.get("nome_empresa")),
        _kv("CNPJ", company.get("cnpj_empresa")),
        _kv("Endereço", company.get("endereco_empresa")),
        _kv("Cidade/UF", company.get("cidade_uf_empresa")),
        _kv("Contatos", _join_values(("Telefone", company.get("telefone")), ("Whats", company.get("whatsapp")))),
        _kv("Redes", _join_values(("E-mail", company.get("email")), ("Insta", company.get("instagram")))),
    ]


def _customer_cells(customer: dict[str, Any]) -> list[Paragraph]:
    document = customer.get("cpf") or customer.get("cnpj")
    return [
        _kv("Cliente", customer.get("nome")),
        _kv("CPF/CNPJ", document),
        _kv("Telefone", customer.get("telefone")),
        _kv("Obs", customer.get("observacoes")),
    ]


def draw_company_customer_header(company: dict[str, Any], customer: dict[str, Any]) -> Table:
    styles = _styles()
    company_lines = _company_cells(company)
    customer_lines = _customer_cells(customer)
    max_rows = max(len(company_lines), len(customer_lines))
    company_lines.extend(_paragraph("", styles["Line"]) for _ in range(max_rows - len(company_lines)))
    customer_lines.extend(_paragraph("", styles["Line"]) for _ in range(max_rows - len(customer_lines)))

    data = [
        [
            _paragraph("<b>DADOS DA EMPRESA</b>", styles["BlockTitle"]),
            _paragraph("<b>DADOS DO CLIENTE</b>", styles["BlockTitle"]),
        ]
    ]
    data.extend([[company_lines[index], customer_lines[index]] for index in range(max_rows)])

    table = Table(data, colWidths=[8.4 * cm, 8.4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, MID),
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, DARK),
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, DARK),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _detail_row(label: str, value: Any) -> Paragraph:
    return _kv(label, value)


def draw_quote_details(company: dict[str, Any]) -> Table:
    return _details_table(
        "DETALHES DO ORÇAMENTO",
        [
            [
                _detail_row("Vendedor", company.get("nome_vendedor")),
                _detail_row("Data", format_date_br(company.get("data_orcamento"))),
                _detail_row("Validade", f"{company.get('validade_dias')} dias" if safe_text(company.get("validade_dias")) else ""),
            ],
            [
                _detail_row("Pagamento", company.get("forma_pagamento")),
                _detail_row("Observações Gerais", company.get("observacoes_gerais")),
                _detail_row("Prazo de entrega", company.get("prazo_entrega")),
            ],
        ],
    )


def draw_order_details(company: dict[str, Any], order_data: dict[str, Any]) -> Table:
    quote = order_data.get("quote", {})
    return _details_table(
        "DETALHES DO PEDIDO",
        [
            [
                _detail_row("Vendedor", company.get("nome_vendedor")),
                _detail_row("Data", format_date_br(order_data.get("data_pedido"))),
                _detail_row("Referência", quote.get("numero_orcamento")),
            ],
            [
                _detail_row("Pagamento", company.get("forma_pagamento")),
                _detail_row("Observações Gerais", company.get("observacoes_gerais")),
                _detail_row("Prazo de entrega", company.get("prazo_entrega")),
            ],
        ],
    )


def _details_table(title: str, rows: list[list[Paragraph]]) -> Table:
    styles = _styles()
    data = [[_paragraph(f"<b>{title}</b>", styles["BlockTitle"]), "", ""]]
    data.extend(rows)
    table = Table(data, colWidths=[5.6 * cm, 5.6 * cm, 5.6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, MID),
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, DARK),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def build_items_table(data: list[list[Any]], col_widths: list[float]) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, LIGHT_GRID),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _quote_items_table(items: list[dict[str, Any]]) -> Table:
    styles = _styles()
    header_style = styles["TableHeader"]
    body_style = styles["Small"]
    header = ["Código", "Descrição", "Avulso", "2 a 4", "5 a 7", "8 a 19", "Acima de 20"]
    data = [[_paragraph(f"<b>{column}</b>", header_style) for column in header]]
    for item in items:
        data.append(
            [
                _paragraph(item.get("produto"), body_style),
                _paragraph(item.get("descricao"), body_style),
                _paragraph(format_brl(item.get("preco_avulso")), body_style),
                _paragraph(format_brl(item.get("preco_2_a_4")), body_style),
                _paragraph(format_brl(item.get("preco_5_a_7")), body_style),
                _paragraph(format_brl(item.get("preco_8_a_19")), body_style),
                _paragraph(format_brl(item.get("preco_acima_20")), body_style),
            ]
        )
    return build_items_table(data, [2.2 * cm, 5.3 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 1.9 * cm, 2.1 * cm])


def _order_items_table(items: list[dict[str, Any]]) -> Table:
    styles = _styles()
    header_style = styles["TableHeader"]
    body_style = styles["Small"]
    header = ["Código", "Descrição", "Qtd.", "Un.", "Métrica", "Preço unit.", "Valor total"]
    data = [[_paragraph(f"<b>{column}</b>", header_style) for column in header]]
    for item in items:
        data.append(
            [
                _paragraph(item.get("produto"), body_style),
                _paragraph(item.get("descricao"), body_style),
                _paragraph(item.get("quantidade"), body_style),
                _paragraph(item.get("unidade"), body_style),
                _paragraph(item.get("metrica_aplicada"), body_style),
                _paragraph(format_brl(item.get("preco_unitario")), body_style),
                _paragraph(format_brl(item.get("valor_total")), body_style),
            ]
        )
    return build_items_table(data, [2.1 * cm, 5.5 * cm, 1.1 * cm, 1.0 * cm, 2.0 * cm, 2.4 * cm, 2.6 * cm])


def _build_document(title: str, number: str, story: list[Any]) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.0 * cm,
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
    story.extend(_document_header("ORÇAMENTO", quote_data.get("numero_orcamento", ""), company.get("data_orcamento"), logo_file))
    story.append(draw_company_customer_header(company, customer))
    story.append(Spacer(1, 0.22 * cm))
    story.append(draw_quote_details(company))
    story.append(Spacer(1, 0.32 * cm))
    story.append(_quote_items_table(items))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_paragraph(f"<b>Total de modelos orçados:</b> {totals.get('total_modelos', len(items))}", styles["Line"]))
    story.append(_paragraph("Observação: Os valores acima são calculados por faixa de quantidade, conforme a métrica selecionada no pedido.", styles["Small"]))
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
    story.extend(_document_header("PEDIDO", order_data.get("numero_pedido", ""), order_data.get("data_pedido"), logo_file))
    story.append(draw_company_customer_header(company, customer))
    story.append(Spacer(1, 0.22 * cm))
    story.append(draw_order_details(company, order_data))
    story.append(Spacer(1, 0.32 * cm))
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

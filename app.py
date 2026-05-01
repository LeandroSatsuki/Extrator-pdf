from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.excel_writer import build_excel
from src.extractor import extract_pdf
from src.models import ITEM_COLUMNS, SUMMARY_COLUMNS
from src.order import calculate_order_totals, create_order_from_quote, recalculate_order_items, validate_order
from src.pdf_writer import build_order_pdf, build_quote_pdf
from src.product_base import build_product_base, find_product_by_code
from src.quote import (
    calculate_quote_totals,
    create_quote_item,
    recalculate_quote_items,
    validate_quote,
)
from src.utils import format_brl, format_weight, generate_order_number, generate_quote_number


st.set_page_config(page_title="Extrator de Itens de Pedido de Venda", layout="wide")


QUOTE_DISPLAY_COLUMNS = [
    "selecionar",
    "produto",
    "descricao",
    "peso_g",
    "unidade",
    "classificacao",
    "quantidade",
    "preco_1_3",
    "preco_4_6",
    "preco_7_9",
    "preco_acima_10",
    "preco_aplicado",
    "valor_total",
    "observacao",
]

ORDER_DISPLAY_COLUMNS = [
    "selecionar",
    "produto",
    "descricao",
    "quantidade_orcamento",
    "quantidade_pedido",
    "unidade",
    "preco_aplicado",
    "valor_total",
    "observacao",
]


def _empty_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.DataFrame(columns=ITEM_COLUMNS), pd.DataFrame(columns=SUMMARY_COLUMNS)


def _default_company_data() -> dict:
    return {
        "nome_empresa": "",
        "cnpj_empresa": "",
        "endereco_empresa": "",
        "cidade_uf_empresa": "",
        "telefone": "",
        "whatsapp": "",
        "email": "",
        "instagram": "",
        "site": "",
        "nome_vendedor": "",
        "data_orcamento": date.today(),
        "validade_dias": 7,
        "forma_pagamento": "",
        "prazo_entrega": "",
        "observacoes_gerais": "",
    }


def _default_customer_data() -> dict:
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


def _init_state() -> None:
    defaults = {
        "items_df": pd.DataFrame(columns=ITEM_COLUMNS),
        "summary_df": pd.DataFrame(columns=SUMMARY_COLUMNS),
        "warnings": [],
        "excel_data": None,
        "pdfs_processados": False,
        "extracao_confirmada": False,
        "base_produtos": pd.DataFrame(),
        "dados_empresa": _default_company_data(),
        "dados_cliente": _default_customer_data(),
        "percentuais_acrescimo": {"1_3": 50.0, "4_6": 45.0, "7_9": 40.0, "acima_10": 35.0},
        "itens_orcamento": [],
        "orcamento_confirmado": False,
        "orcamento_confirmado_data": None,
        "numero_orcamento": "",
        "pdf_orcamento": None,
        "itens_pedido": [],
        "pedido_confirmado": False,
        "pedido_confirmado_data": None,
        "numero_pedido": "",
        "pdf_pedido": None,
        "logo": None,
        "produto_encontrado": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _process_files(uploaded_files) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    all_items = []
    summaries = []
    warnings = []

    for uploaded_file in uploaded_files:
        result = extract_pdf(uploaded_file.getvalue(), uploaded_file.name)
        all_items.extend(result["items"])
        summaries.append(result["summary"])
        warnings.extend(result["warnings"])

    items_df = pd.DataFrame(all_items, columns=ITEM_COLUMNS)
    summary_df = pd.DataFrame(summaries, columns=SUMMARY_COLUMNS)
    return items_df, summary_df, warnings


def _reset_commercial_flow(keep_customer: bool = False) -> None:
    if not keep_customer:
        st.session_state["dados_cliente"] = _default_customer_data()
    st.session_state["itens_orcamento"] = []
    st.session_state["orcamento_confirmado"] = False
    st.session_state["orcamento_confirmado_data"] = None
    st.session_state["numero_orcamento"] = ""
    st.session_state["pdf_orcamento"] = None
    st.session_state["itens_pedido"] = []
    st.session_state["pedido_confirmado"] = False
    st.session_state["pedido_confirmado_data"] = None
    st.session_state["numero_pedido"] = ""
    st.session_state["pdf_pedido"] = None
    st.session_state["produto_encontrado"] = None


def _invalidate_quote() -> None:
    st.session_state["orcamento_confirmado"] = False
    st.session_state["orcamento_confirmado_data"] = None
    st.session_state["pdf_orcamento"] = None
    st.session_state["pedido_confirmado"] = False
    st.session_state["pedido_confirmado_data"] = None
    st.session_state["pdf_pedido"] = None


def _money_columns_config(prefix: str = "") -> dict:
    return {
        "preco_1_3": st.column_config.NumberColumn(f"{prefix}Preço 1 a 3", format="R$ %.2f"),
        "preco_4_6": st.column_config.NumberColumn(f"{prefix}Preço 4 a 6", format="R$ %.2f"),
        "preco_7_9": st.column_config.NumberColumn(f"{prefix}Preço 7 a 9", format="R$ %.2f"),
        "preco_acima_10": st.column_config.NumberColumn(f"{prefix}Preço acima de 10", format="R$ %.2f"),
        "preco_aplicado": st.column_config.NumberColumn(f"{prefix}Preço aplicado", format="R$ %.2f"),
        "valor_total": st.column_config.NumberColumn(f"{prefix}Valor total", format="R$ %.2f"),
    }


def _render_refazer_orcamento(location: str) -> None:
    st.divider()
    st.subheader("Refazer orçamento")
    confirm_key = f"confirm_refazer_{location}"
    if st.checkbox("Confirmo que desejo refazer o orçamento", key=confirm_key):
        if st.button("Refazer orçamento", key=f"refazer_{location}"):
            _reset_commercial_flow()
            st.success("Orçamento e pedido foram limpos. A base importada, a logo, os percentuais e os dados da empresa foram mantidos.")
            st.rerun()


def _render_import_tab() -> None:
    st.header("Importar PDFs")
    uploaded_files = st.file_uploader(
        "Selecione até 5 arquivos PDF",
        type=["pdf"],
        accept_multiple_files=True,
    )

    too_many_files = len(uploaded_files) > 5
    if too_many_files:
        st.error("Selecione no máximo 5 arquivos PDF.")

    process_clicked = st.button(
        "Processar PDFs",
        type="primary",
        disabled=not uploaded_files or too_many_files,
    )

    if process_clicked:
        with st.spinner("Processando PDFs..."):
            items_df, summary_df, warnings = _process_files(uploaded_files)
            st.session_state["items_df"] = items_df
            st.session_state["summary_df"] = summary_df
            st.session_state["warnings"] = warnings
            st.session_state["excel_data"] = build_excel(items_df, summary_df)
            st.session_state["pdfs_processados"] = True
            st.session_state["extracao_confirmada"] = False
            st.session_state["base_produtos"] = pd.DataFrame()
            _reset_commercial_flow()

    items_df = st.session_state["items_df"]
    summary_df = st.session_state["summary_df"]
    warnings = st.session_state["warnings"]

    if summary_df.empty:
        st.info("Importe PDFs de Pedido de Venda para iniciar.")
        return

    st.subheader("Resumo do processamento")
    col_pdf, col_rows = st.columns(2)
    col_pdf.metric("PDFs selecionados", len(summary_df))
    col_rows.metric("Total de linhas processadas", int(summary_df["linhas_extraidas"].sum()))
    st.dataframe(summary_df, width="stretch", hide_index=True)

    if not summary_df[summary_df["status_pdf"].eq("DIVERGENTE")].empty:
        st.error("Há PDFs com quantidade de itens divergente. Confira o resumo antes de avançar.")
    if not summary_df[summary_df["status_pdf"].eq("NÃO ENCONTRADO")].empty:
        st.warning("Há PDFs sem a informação 'Itens:' no rodapé.")
    if not summary_df[summary_df["status_pdf"].eq("ERRO")].empty:
        st.error("Há PDFs que não puderam ser processados. Confira as observações no resumo.")
    for warning in warnings:
        st.warning(warning)

    st.subheader("Prévia dos itens extraídos")
    if items_df.empty:
        st.info("Nenhuma linha de item foi extraída dos PDFs selecionados.")
    else:
        st.dataframe(items_df, width="stretch", hide_index=True)

    confirmed = st.checkbox("Conferi a prévia e confirmo a geração da planilha Excel")
    col_confirm, col_download = st.columns([1, 1])
    with col_confirm:
        if st.button("Confirmar extração", disabled=not confirmed or items_df.empty):
            st.session_state["base_produtos"] = build_product_base(items_df)
            st.session_state["extracao_confirmada"] = True
            st.success("Extração confirmada. A base temporária de produtos foi criada.")
    with col_download:
        if confirmed:
            st.download_button(
                "Baixar Excel",
                data=st.session_state["excel_data"] or build_excel(items_df, summary_df),
                file_name="itens_pedido_venda.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
            )

    if st.session_state["extracao_confirmada"]:
        base = st.session_state["base_produtos"]
        st.success(f"Base de produtos disponível com {len(base)} produto(s) consolidado(s).")
        if not base.empty:
            st.dataframe(
                base[["produto", "descricao", "peso_g", "unidade", "classificacao", "observacao"]],
                width="stretch",
                hide_index=True,
            )


def _render_company_form() -> dict:
    data = st.session_state["dados_empresa"]
    st.subheader("Dados da empresa / vendedor")
    col1, col2, col3 = st.columns(3)
    data["nome_empresa"] = col1.text_input("Nome da empresa", value=data.get("nome_empresa", ""))
    data["cnpj_empresa"] = col2.text_input("CNPJ da empresa", value=data.get("cnpj_empresa", ""))
    data["cidade_uf_empresa"] = col3.text_input("Cidade/UF da empresa", value=data.get("cidade_uf_empresa", ""))
    data["endereco_empresa"] = st.text_input("Endereço da empresa", value=data.get("endereco_empresa", ""))

    col4, col5, col6 = st.columns(3)
    data["telefone"] = col4.text_input("Telefone", value=data.get("telefone", ""))
    data["whatsapp"] = col5.text_input("WhatsApp", value=data.get("whatsapp", ""))
    data["email"] = col6.text_input("Email", value=data.get("email", ""))

    col7, col8, col9 = st.columns(3)
    data["instagram"] = col7.text_input("Instagram", value=data.get("instagram", ""))
    data["site"] = col8.text_input("Site", value=data.get("site", ""))
    data["nome_vendedor"] = col9.text_input("Nome do vendedor", value=data.get("nome_vendedor", ""))

    col10, col11, col12 = st.columns(3)
    data["data_orcamento"] = col10.date_input("Data do orçamento", value=data.get("data_orcamento") or date.today())
    data["validade_dias"] = col11.number_input("Validade do orçamento em dias", min_value=1, step=1, value=int(data.get("validade_dias") or 7))
    data["prazo_entrega"] = col12.text_input("Prazo de entrega", value=data.get("prazo_entrega", ""))
    data["forma_pagamento"] = st.text_input("Forma de pagamento", value=data.get("forma_pagamento", ""))
    data["observacoes_gerais"] = st.text_area("Observações gerais", value=data.get("observacoes_gerais", ""), height=80)

    logo_file = st.file_uploader("Logo para os PDFs (PNG, JPG ou JPEG)", type=["png", "jpg", "jpeg"])
    if logo_file is not None:
        st.session_state["logo"] = logo_file.getvalue()
        st.success("Logo carregada para orçamento e pedido.")

    st.session_state["dados_empresa"] = data
    return data


def _render_customer_form() -> dict:
    data = st.session_state["dados_cliente"]
    st.subheader("Dados do cliente")
    data["nome"] = st.text_input("Nome do cliente", value=data.get("nome", ""))
    col1, col2, col3 = st.columns(3)
    data["cpf"] = col1.text_input("CPF", value=data.get("cpf", ""))
    data["cnpj"] = col2.text_input("CNPJ", value=data.get("cnpj", ""))
    data["telefone"] = col3.text_input("Telefone do cliente", value=data.get("telefone", ""))
    col4, col5, col6 = st.columns(3)
    data["email"] = col4.text_input("Email do cliente", value=data.get("email", ""))
    data["cidade"] = col5.text_input("Cidade", value=data.get("cidade", ""))
    data["uf"] = col6.text_input("UF", value=data.get("uf", ""), max_chars=2)
    data["endereco"] = st.text_input("Endereço do cliente", value=data.get("endereco", ""))
    data["observacoes"] = st.text_area("Observações do cliente", value=data.get("observacoes", ""), height=80)
    st.session_state["dados_cliente"] = data
    return data


def _render_percentages() -> dict:
    st.subheader("Percentuais de acréscimo por faixa")
    previous = dict(st.session_state["percentuais_acrescimo"])
    percentages = dict(previous)
    col1, col2, col3, col4 = st.columns(4)
    percentages["1_3"] = col1.number_input("Acréscimo 1 a 3 unidades (%)", min_value=0.0, step=1.0, value=float(percentages.get("1_3", 0)))
    percentages["4_6"] = col2.number_input("Acréscimo 4 a 6 unidades (%)", min_value=0.0, step=1.0, value=float(percentages.get("4_6", 0)))
    percentages["7_9"] = col3.number_input("Acréscimo 7 a 9 unidades (%)", min_value=0.0, step=1.0, value=float(percentages.get("7_9", 0)))
    percentages["acima_10"] = col4.number_input("Acréscimo acima de 10 unidades (%)", min_value=0.0, step=1.0, value=float(percentages.get("acima_10", 0)))
    st.session_state["percentuais_acrescimo"] = percentages
    if percentages != previous:
        st.session_state["itens_orcamento"] = recalculate_quote_items(st.session_state["itens_orcamento"], percentages)
        _invalidate_quote()
    return percentages


def _render_product_search(percentages: dict) -> None:
    st.subheader("Adicionar item")
    col_code, col_qty, col_search = st.columns([2, 1, 1])
    code = col_code.text_input("Código do produto", key="codigo_busca_produto")
    quantity = col_qty.number_input("Quantidade desejada", min_value=1, step=1, value=1, key="quantidade_busca_produto")

    if col_search.button("Buscar item"):
        product = find_product_by_code(st.session_state["base_produtos"], code)
        if not product:
            st.session_state["produto_encontrado"] = None
            st.error("Produto não encontrado na base importada.")
        else:
            st.session_state["produto_encontrado"] = product
            if product.get("tem_divergencia"):
                st.warning("Produto encontrado em mais de um PDF com dados divergentes.")
            st.success("Produto encontrado.")

    product = st.session_state.get("produto_encontrado")
    if not product:
        return

    preview = create_quote_item(product, int(quantity), percentages)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "produto": preview["produto"],
                    "descricao": preview["descricao"],
                    "peso": format_weight(preview["peso_g"]),
                    "unidade": preview["unidade"],
                    "classificacao": preview["classificacao"],
                    "preço 1 a 3": format_brl(preview["preco_1_3"]),
                    "preço 4 a 6": format_brl(preview["preco_4_6"]),
                    "preço 7 a 9": format_brl(preview["preco_7_9"]),
                    "preço acima de 10": format_brl(preview["preco_acima_10"]),
                    "valor base interno": format_brl(product.get("valor_unitario_original")),
                    "observação": preview["observacao"],
                }
            ]
        ),
        width="stretch",
        hide_index=True,
    )

    if st.button("Adicionar item"):
        st.session_state["itens_orcamento"].append(preview)
        _invalidate_quote()
        st.success("Item adicionado ao orçamento.")


def _render_quote_items(percentages: dict) -> None:
    st.subheader("Tabela de itens do orçamento")
    items = st.session_state["itens_orcamento"]
    if not items:
        st.info("Nenhum item adicionado ao orçamento.")
        return

    df = pd.DataFrame(items)
    edited = st.data_editor(
        df[QUOTE_DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
        disabled=[
            "produto",
            "descricao",
            "peso_g",
            "unidade",
            "classificacao",
            "preco_1_3",
            "preco_4_6",
            "preco_7_9",
            "preco_acima_10",
            "preco_aplicado",
            "valor_total",
            "observacao",
        ],
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Selecionar"),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, step=1),
            **_money_columns_config(),
        },
        key="quote_items_editor",
    )

    full_df = df.copy()
    for column in ["selecionar", "quantidade"]:
        full_df[column] = edited[column]
    updated_items = recalculate_quote_items(full_df.to_dict("records"), percentages)
    if updated_items != items:
        st.session_state["itens_orcamento"] = updated_items
        _invalidate_quote()

    col_recalc, col_remove, col_clear = st.columns(3)
    if col_recalc.button("Recalcular orçamento"):
        st.session_state["itens_orcamento"] = recalculate_quote_items(st.session_state["itens_orcamento"], percentages)
        _invalidate_quote()
        st.success("Orçamento recalculado.")
        st.rerun()

    if col_remove.button("Remover itens desmarcados"):
        st.session_state["itens_orcamento"] = [item for item in st.session_state["itens_orcamento"] if item.get("selecionar", True)]
        _invalidate_quote()
        st.rerun()

    if col_clear.button("Limpar orçamento"):
        st.session_state["itens_orcamento"] = []
        _invalidate_quote()
        st.rerun()

    totals = calculate_quote_totals(st.session_state["itens_orcamento"])
    col_qty, col_total = st.columns(2)
    col_qty.metric("Quantidade total de itens", totals["quantidade_total"])
    col_total.metric("Valor total do orçamento", format_brl(totals["valor_total"]))


def _render_quote_tab() -> None:
    if not st.session_state["extracao_confirmada"]:
        st.warning("Importe e confirme os PDFs antes de criar orçamentos ou pedidos.")
        return

    st.header("Orçamento")
    base = st.session_state["base_produtos"]
    st.caption(f"Base temporária: {len(base)} produto(s) importado(s). O valor original é usado apenas como referência interna de cálculo.")

    company_data = _render_company_form()
    customer_data = _render_customer_form()
    percentages = _render_percentages()
    _render_product_search(percentages)
    _render_quote_items(percentages)

    errors = validate_quote(customer_data, company_data, st.session_state["itens_orcamento"], percentages)
    if st.button("Confirmar orçamento", type="primary"):
        if errors:
            for error in errors:
                st.error(error)
        else:
            numero = st.session_state["numero_orcamento"] or generate_quote_number()
            totals = calculate_quote_totals(st.session_state["itens_orcamento"])
            quote_data = {
                "numero_orcamento": numero,
                "company_data": dict(company_data),
                "customer_data": dict(customer_data),
                "percentages": dict(percentages),
                "items": list(st.session_state["itens_orcamento"]),
                "totals": totals,
            }
            st.session_state["numero_orcamento"] = numero
            st.session_state["orcamento_confirmado"] = True
            st.session_state["orcamento_confirmado_data"] = quote_data
            st.session_state["pdf_orcamento"] = build_quote_pdf(quote_data, st.session_state.get("logo"))
            st.success(f"Orçamento {numero} confirmado.")

    if st.session_state["orcamento_confirmado"]:
        st.download_button(
            "Baixar PDF do orçamento",
            data=st.session_state["pdf_orcamento"],
            file_name=f"{st.session_state['numero_orcamento']}.pdf",
            mime="application/pdf",
        )
        if st.button("Gerar pedido a partir deste orçamento"):
            quote_data = st.session_state["orcamento_confirmado_data"]
            st.session_state["itens_pedido"] = create_order_from_quote(quote_data)
            st.session_state["pedido_confirmado"] = False
            st.session_state["pdf_pedido"] = None
            st.success("Pedido criado a partir do orçamento confirmado. Acesse a aba Pedido.")
    elif st.session_state["numero_orcamento"]:
        st.warning("Há alterações no orçamento. Confirme novamente antes de baixar o PDF ou gerar pedido.")

    _render_refazer_orcamento("orcamento")


def _render_order_tab() -> None:
    if not st.session_state["extracao_confirmada"]:
        st.warning("Importe e confirme os PDFs antes de criar orçamentos ou pedidos.")
        return

    if not st.session_state["orcamento_confirmado"] or not st.session_state["orcamento_confirmado_data"]:
        st.warning("Confirme um orçamento antes de gerar o pedido.")
        return

    st.header("Pedido")
    quote_data = st.session_state["orcamento_confirmado_data"]
    st.write(f"Orçamento confirmado: **{quote_data['numero_orcamento']}**")
    st.write(f"Cliente: **{quote_data['customer_data'].get('nome', '')}**")

    if not st.session_state["itens_pedido"]:
        st.session_state["itens_pedido"] = create_order_from_quote(quote_data)

    items = st.session_state["itens_pedido"]
    df = pd.DataFrame(items)
    edited = st.data_editor(
        df[ORDER_DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
        disabled=["produto", "descricao", "quantidade_orcamento", "unidade", "preco_aplicado", "valor_total", "observacao"],
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Selecionar"),
            "quantidade_pedido": st.column_config.NumberColumn("Quantidade pedido", min_value=1, step=1),
            "preco_aplicado": st.column_config.NumberColumn("Preço aplicado", format="R$ %.2f"),
            "valor_total": st.column_config.NumberColumn("Valor total", format="R$ %.2f"),
        },
        key="order_items_editor",
    )

    full_df = df.copy()
    for column in ["selecionar", "quantidade_pedido"]:
        full_df[column] = edited[column]
    updated_items = recalculate_order_items(full_df.to_dict("records"), quote_data["percentages"])
    if updated_items != items:
        st.session_state["itens_pedido"] = updated_items
        st.session_state["pedido_confirmado"] = False
        st.session_state["pdf_pedido"] = None

    col_recalc, col_back = st.columns(2)
    if col_recalc.button("Recalcular pedido"):
        st.session_state["itens_pedido"] = recalculate_order_items(st.session_state["itens_pedido"], quote_data["percentages"])
        st.session_state["pedido_confirmado"] = False
        st.session_state["pdf_pedido"] = None
        st.success("Pedido recalculado.")
        st.rerun()
    if col_back.button("Voltar para orçamento"):
        st.info("Use a aba Orçamento para revisar os dados.")

    totals = calculate_order_totals(st.session_state["itens_pedido"])
    col_qty, col_total = st.columns(2)
    col_qty.metric("Quantidade total", totals["quantidade_total"])
    col_total.metric("Valor total do pedido", format_brl(totals["valor_total"]))

    if st.button("Confirmar pedido", type="primary"):
        order_data = {
            "numero_pedido": st.session_state["numero_pedido"] or generate_order_number(),
            "data_pedido": date.today(),
            "quote": quote_data,
            "items": st.session_state["itens_pedido"],
            "totals": totals,
        }
        errors = validate_order(order_data)
        if errors:
            for error in errors:
                st.error(error)
        else:
            st.session_state["numero_pedido"] = order_data["numero_pedido"]
            st.session_state["pedido_confirmado"] = True
            st.session_state["pedido_confirmado_data"] = order_data
            st.session_state["pdf_pedido"] = build_order_pdf(order_data, st.session_state.get("logo"))
            st.success(f"Pedido {order_data['numero_pedido']} confirmado.")

    if st.session_state["pedido_confirmado"]:
        st.download_button(
            "Baixar PDF do pedido",
            data=st.session_state["pdf_pedido"],
            file_name=f"{st.session_state['numero_pedido']}.pdf",
            mime="application/pdf",
        )

    _render_refazer_orcamento("pedido")


_init_state()

st.title("Extrator de Itens de Pedido de Venda")

tab_import, tab_quote, tab_order = st.tabs(["Importar PDFs", "Orçamento", "Pedido"])

with tab_import:
    _render_import_tab()

with tab_quote:
    _render_quote_tab()

with tab_order:
    _render_order_tab()

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from src.excel_writer import build_excel
from src.extractor import extract_pdf
from src.models import ITEM_COLUMNS, SUMMARY_COLUMNS
from src.order import calculate_order_totals, create_order_from_quote, recalculate_order_items, validate_order
from src.persistence import (
    get_empty_customer_data,
    load_last_header_data,
    save_last_header_data,
)
from src.pdf_writer import build_order_pdf, build_quote_pdf
from src.pricing import MARKUP_KEYS, markup_sequence_has_warning
from src.product_base import build_product_base, format_product_option, normalize_product_code, search_products
from src.quote import calculate_quote_totals, create_quote_item, recalculate_quote_items, validate_quote
from src.utils import (
    configure_file_logging,
    format_brl,
    format_weight,
    generate_order_number,
    generate_quote_number,
    get_default_logo_path,
    get_logo_source,
)


st.set_page_config(page_title="Extrator de Itens de Pedido de Venda", layout="wide")


LOGGER = configure_file_logging("extrator_pdf.app")
MAX_PDF_FILES = 5
MAX_PDF_SIZE_MB = 50
MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024


QUOTE_DISPLAY_COLUMNS = [
    "selecionar",
    "produto",
    "descricao",
    "peso_g",
    "unidade",
    "classificacao",
    "preco_avulso",
    "preco_3_pecas",
    "preco_5_pecas",
    "preco_10_pecas",
    "preco_20_pecas_alto_atacado",
    "observacao",
]

ORDER_DISPLAY_COLUMNS = [
    "selecionar",
    "produto",
    "descricao",
    "quantidade",
    "unidade",
    "metrica_aplicada",
    "preco_unitario",
    "valor_total",
    "valor_se_avulso",
    "observacao",
]

IMPORT_PREVIEW_HIDDEN_COLUMNS = {"valor_base", "percentual", "valor_unitario", "valor_total"}


def _default_company_data() -> dict:
    saved_header = load_last_header_data()
    return {
        **saved_header["company_data"],
        **saved_header["commercial_data"],
        "data_orcamento": date.today(),
    }


def _default_customer_data() -> dict:
    return get_empty_customer_data()


def _default_markups() -> dict:
    return {
        "acrescimo_avulso": 80.0,
        "acrescimo_3_pecas": 70.0,
        "acrescimo_5_pecas": 60.0,
        "acrescimo_10_pecas": 50.0,
        "acrescimo_20_pecas_alto_atacado": 40.0,
    }


def _normalize_percentages(value: dict | None) -> dict:
    value = value or {}
    if all(key in value for key in MARKUP_KEYS):
        return {key: float(value.get(key) or 0) for key in MARKUP_KEYS}
    defaults = _default_markups()
    legacy = {
        "acrescimo_avulso": value.get("acrescimo_avulso", value.get("1_3", defaults["acrescimo_avulso"])),
        "acrescimo_3_pecas": value.get("acrescimo_3_pecas", value.get("acrescimo_2_a_4", value.get("4_6", defaults["acrescimo_3_pecas"]))),
        "acrescimo_5_pecas": value.get("acrescimo_5_pecas", value.get("acrescimo_5_a_7", value.get("7_9", defaults["acrescimo_5_pecas"]))),
        "acrescimo_10_pecas": value.get("acrescimo_10_pecas", value.get("acrescimo_8_a_19", value.get("acima_10", defaults["acrescimo_10_pecas"]))),
        "acrescimo_20_pecas_alto_atacado": value.get("acrescimo_20_pecas_alto_atacado", value.get("acrescimo_acima_20", defaults["acrescimo_20_pecas_alto_atacado"])),
    }
    return {key: float(legacy.get(key) or 0) for key in MARKUP_KEYS}


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
        "percentuais_acrescimo": _default_markups(),
        "itens_orcamento": [],
        "orcamento_confirmado": False,
        "orcamento_em_edicao": False,
        "orcamento_confirmado_data": None,
        "numero_orcamento": "",
        "pdf_orcamento": None,
        "itens_pedido": [],
        "pedido_em_edicao": False,
        "pedido_confirmado": False,
        "pedido_confirmado_data": None,
        "pedido_quantidades_confirmadas": True,
        "pedido_tem_alteracao_pendente": False,
        "numero_pedido": "",
        "pdf_pedido": None,
        "logo": None,
        "produto_encontrado": None,
        "produtos_encontrados": [],
        "active_page": "Importar PDFs",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    st.session_state["percentuais_acrescimo"] = _normalize_percentages(st.session_state.get("percentuais_acrescimo"))
    _sync_header_aliases()


def _sync_header_aliases() -> None:
    company = st.session_state["dados_empresa"]
    st.session_state["company_data"] = {
        key: company.get(key, "")
        for key in (
            "nome_empresa",
            "cnpj_empresa",
            "endereco_empresa",
            "cidade_uf_empresa",
            "telefone",
            "whatsapp",
            "email",
            "instagram",
            "nome_vendedor",
        )
    }
    st.session_state["commercial_data"] = {
        key: company.get(key, "")
        for key in (
            "forma_pagamento",
            "prazo_entrega",
            "validade_dias",
            "observacoes_gerais",
        )
    }
    st.session_state["customer_data"] = st.session_state["dados_cliente"]


def _save_header_defaults(company_data: dict, *, show_message: bool = True) -> bool:
    saved = save_last_header_data(company_data, company_data)
    if show_message:
        if saved:
            st.success("Dados do cabeçalho salvos como padrão.")
        else:
            st.error("Não foi possível salvar os dados do cabeçalho como padrão.")
    return saved


def _process_files(uploaded_files) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    all_items = []
    summaries = []
    warnings = []
    for uploaded_file in uploaded_files:
        try:
            result = extract_pdf(uploaded_file.getvalue(), uploaded_file.name)
        except Exception as exc:
            LOGGER.exception("Falha inesperada ao processar o arquivo %s", getattr(uploaded_file, "name", "desconhecido"))
            result = {
                "items": [],
                "summary": {
                    "arquivo_origem": getattr(uploaded_file, "name", "arquivo_desconhecido.pdf"),
                    "numero_pedido": "",
                    "cliente": "",
                    "faturamento": "",
                    "linhas_extraidas": 0,
                    "linhas_ok": 0,
                    "linhas_conferir": 0,
                    "itens_rodape": None,
                    "status_pdf": "ERRO",
                    "observacoes_pdf": f"Erro inesperado ao processar o PDF: {exc}",
                },
                "warnings": [f"Falha ao processar {getattr(uploaded_file, 'name', 'o arquivo')}: {exc}"],
            }
        all_items.extend(result["items"])
        summaries.append(result["summary"])
        warnings.extend(result["warnings"])
    return pd.DataFrame(all_items, columns=ITEM_COLUMNS), pd.DataFrame(summaries, columns=SUMMARY_COLUMNS), warnings


def _clear_commercial_on_new_import() -> None:
    st.session_state["dados_cliente"] = _default_customer_data()
    st.session_state["itens_orcamento"] = []
    st.session_state["orcamento_confirmado"] = False
    st.session_state["orcamento_em_edicao"] = False
    st.session_state["orcamento_confirmado_data"] = None
    st.session_state["numero_orcamento"] = ""
    st.session_state["pdf_orcamento"] = None
    st.session_state["itens_pedido"] = []
    st.session_state["pedido_em_edicao"] = False
    st.session_state["pedido_confirmado"] = False
    st.session_state["pedido_confirmado_data"] = None
    st.session_state["pedido_quantidades_confirmadas"] = True
    st.session_state["pedido_tem_alteracao_pendente"] = False
    st.session_state["numero_pedido"] = ""
    st.session_state["pdf_pedido"] = None
    st.session_state["produto_encontrado"] = None
    st.session_state["produtos_encontrados"] = []
    _sync_header_aliases()


def _invalidate_quote() -> None:
    has_confirmed_quote = bool(
        st.session_state.get("numero_orcamento")
        or st.session_state.get("orcamento_confirmado")
        or st.session_state.get("orcamento_confirmado_data")
    )
    st.session_state["orcamento_confirmado"] = False
    st.session_state["orcamento_em_edicao"] = has_confirmed_quote
    st.session_state["orcamento_confirmado_data"] = None
    st.session_state["pdf_orcamento"] = None
    st.session_state["pedido_confirmado"] = False
    st.session_state["pedido_confirmado_data"] = None
    st.session_state["pdf_pedido"] = None
    if st.session_state.get("itens_pedido"):
        st.session_state["pedido_tem_alteracao_pendente"] = True
        st.session_state["pedido_quantidades_confirmadas"] = False


def _logo_bytes() -> bytes | None:
    return get_logo_source(st.session_state.get("logo"))


def _render_edit_quote_button(location: str) -> None:
    if st.button("Editar orçamento / Refazer orçamento", key=f"edit_quote_{location}"):
        st.session_state["orcamento_confirmado"] = False
        st.session_state["orcamento_em_edicao"] = True
        st.session_state["pdf_orcamento"] = None
        st.session_state["pedido_confirmado"] = False
        st.session_state["pedido_confirmado_data"] = None
        st.session_state["pdf_pedido"] = None
        if st.session_state.get("itens_pedido"):
            st.session_state["pedido_tem_alteracao_pendente"] = True
            st.session_state["pedido_quantidades_confirmadas"] = False
        st.session_state["active_page"] = "Orçamento"
        st.success("Orçamento liberado para edição. Confirme novamente para gerar PDF ou pedido atualizado.")
        st.rerun()


def _money_columns_config() -> dict:
    return {
        "preco_avulso": st.column_config.NumberColumn("Avulso", format="R$ %.2f"),
        "preco_3_pecas": st.column_config.NumberColumn("3 peças", format="R$ %.2f"),
        "preco_5_pecas": st.column_config.NumberColumn("5 peças", format="R$ %.2f"),
        "preco_10_pecas": st.column_config.NumberColumn("10 peças", format="R$ %.2f"),
        "preco_20_pecas_alto_atacado": st.column_config.NumberColumn("20 peças (alto atacado)", format="R$ %.2f"),
        "preco_unitario": st.column_config.NumberColumn("Preço unitário", format="R$ %.2f"),
        "valor_total": st.column_config.NumberColumn("Valor total", format="R$ %.2f"),
        "valor_se_avulso": st.column_config.NumberColumn("Valor se avulso", format="R$ %.2f"),
    }


def _render_import_tab() -> None:
    st.header("Importar PDFs")
    uploaded_files = st.file_uploader("Selecione até 5 arquivos PDF", type=["pdf"], accept_multiple_files=True)

    too_many_files = len(uploaded_files) > MAX_PDF_FILES
    oversized_files = [
        f"{uploaded_file.name} ({uploaded_file.size / (1024 * 1024):.1f} MB)"
        for uploaded_file in uploaded_files
        if getattr(uploaded_file, "size", 0) > MAX_PDF_SIZE_BYTES
    ]
    has_oversized_files = bool(oversized_files)
    if too_many_files:
        st.error(f"Selecione no máximo {MAX_PDF_FILES} arquivos PDF.")
    if has_oversized_files:
        st.error(
            "Cada PDF deve ter no máximo 50 MB. Arquivos acima do limite: "
            + ", ".join(oversized_files)
        )

    if st.button("Processar PDFs", type="primary", disabled=not uploaded_files or too_many_files or has_oversized_files):
        try:
            with st.spinner("Processando PDFs..."):
                items_df, summary_df, warnings = _process_files(uploaded_files)
                st.session_state["items_df"] = items_df
                st.session_state["summary_df"] = summary_df
                st.session_state["warnings"] = warnings
                st.session_state["excel_data"] = build_excel(items_df, summary_df).getvalue()
                st.session_state["pdfs_processados"] = True
                st.session_state["extracao_confirmada"] = False
                st.session_state["base_produtos"] = pd.DataFrame()
                _clear_commercial_on_new_import()
        except Exception as exc:
            LOGGER.exception("Erro ao processar o lote de PDFs")
            st.error(f"Ocorreu um erro ao processar os PDFs: {exc}")

    items_df = st.session_state["items_df"]
    summary_df = st.session_state["summary_df"]
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
    for warning in st.session_state["warnings"]:
        st.warning(warning)

    st.subheader("Prévia dos itens extraídos")
    if items_df.empty:
        st.info("Nenhuma linha de item foi extraída dos PDFs selecionados.")
    else:
        preview_columns = [column for column in items_df.columns if column not in IMPORT_PREVIEW_HIDDEN_COLUMNS]
        st.dataframe(items_df[preview_columns], width="stretch", hide_index=True)

    confirmed = st.checkbox("Conferi a prévia e confirmo a geração da planilha Excel")
    col_confirm, col_download = st.columns(2)
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
            st.dataframe(base[["produto", "descricao", "peso_g", "unidade", "classificacao", "observacao"]], width="stretch", hide_index=True)


def _company_is_filled(data: dict) -> bool:
    return bool(data.get("nome_empresa") and data.get("nome_vendedor") and (data.get("telefone") or data.get("email")))


def _customer_is_filled(data: dict) -> bool:
    return bool(data.get("nome"))


def _render_company_form() -> dict:
    data = st.session_state["dados_empresa"]
    previous = dict(data)
    with st.expander("Dados da empresa / vendedor", expanded=not _company_is_filled(data)):
        col1, col2, col3 = st.columns(3)
        data["nome_empresa"] = col1.text_input("Nome da empresa", value=data.get("nome_empresa", ""))
        data["cnpj_empresa"] = col2.text_input("CNPJ da empresa", value=data.get("cnpj_empresa", ""))
        data["cidade_uf_empresa"] = col3.text_input("Cidade/UF da empresa", value=data.get("cidade_uf_empresa", ""))
        data["endereco_empresa"] = st.text_input("Endereço da empresa", value=data.get("endereco_empresa", ""))
        col4, col5, col6 = st.columns(3)
        data["telefone"] = col4.text_input("Telefone", value=data.get("telefone", ""))
        data["whatsapp"] = col5.text_input("WhatsApp", value=data.get("whatsapp", ""))
        data["email"] = col6.text_input("Email", value=data.get("email", ""))
        col7, col8 = st.columns(2)
        data["instagram"] = col7.text_input("Instagram", value=data.get("instagram", ""))
        data["nome_vendedor"] = col8.text_input("Nome do vendedor", value=data.get("nome_vendedor", ""))

        default_logo = get_default_logo_path()
        if default_logo.exists() and st.session_state.get("logo") is None:
            st.caption("Usando automaticamente a logo fixa em assets/logo.png.")
        logo_file = st.file_uploader("Substituir logo temporariamente (PNG, JPG ou JPEG)", type=["png", "jpg", "jpeg"])
        if logo_file is not None:
            st.session_state["logo"] = logo_file.getvalue()
            _invalidate_quote()
            st.success("Logo temporária carregada para orçamento e pedido.")
        if _logo_bytes():
            st.image(_logo_bytes(), width=220)
        if st.button("Salvar dados do cabeçalho como padrão", key="save_header_company"):
            _save_header_defaults(data)

    st.session_state["dados_empresa"] = data
    _sync_header_aliases()
    if data != previous:
        _invalidate_quote()
    return data


def _render_customer_form() -> dict:
    data = st.session_state["dados_cliente"]
    previous = dict(data)
    with st.expander("Dados do cliente", expanded=not _customer_is_filled(data)):
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
    _sync_header_aliases()
    if data != previous:
        _invalidate_quote()
    return data


def _render_commercial_terms() -> dict:
    data = st.session_state["dados_empresa"]
    previous = dict(data)
    with st.expander("Condições comerciais", expanded=False):
        col1, col2, col3 = st.columns(3)
        data["data_orcamento"] = col1.date_input("Data do orçamento", value=data.get("data_orcamento") or date.today())
        data["validade_dias"] = col2.number_input("Validade do orçamento em dias", min_value=1, step=1, value=int(data.get("validade_dias") or 7))
        data["prazo_entrega"] = col3.text_input("Prazo de entrega", value=data.get("prazo_entrega", ""))
        data["forma_pagamento"] = st.text_input("Forma de pagamento", value=data.get("forma_pagamento", ""))
        data["observacoes_gerais"] = st.text_area("Observações gerais", value=data.get("observacoes_gerais", ""), height=80)
        if st.button("Salvar dados do cabeçalho como padrão", key="save_header_commercial"):
            _save_header_defaults(data)
    st.session_state["dados_empresa"] = data
    _sync_header_aliases()
    if data != previous:
        _invalidate_quote()
    return data


def _render_percentages() -> dict:
    previous = dict(st.session_state["percentuais_acrescimo"])
    percentages = dict(previous)
    with st.expander("Percentuais de acréscimo", expanded=not st.session_state.get("orcamento_confirmado")):
        st.caption("Os percentuais abaixo são acréscimos sobre o custo da base, não descontos.")
        col1, col2, col3, col4, col5 = st.columns(5)
        percentages["acrescimo_avulso"] = col1.number_input("Acréscimo Avulso (%)", min_value=0.0, step=0.5, value=float(percentages.get("acrescimo_avulso", 0)))
        percentages["acrescimo_3_pecas"] = col2.number_input("Acréscimo 3 peças (%)", min_value=0.0, step=0.5, value=float(percentages.get("acrescimo_3_pecas", 0)))
        percentages["acrescimo_5_pecas"] = col3.number_input("Acréscimo 5 peças (%)", min_value=0.0, step=0.5, value=float(percentages.get("acrescimo_5_pecas", 0)))
        percentages["acrescimo_10_pecas"] = col4.number_input("Acréscimo 10 peças (%)", min_value=0.0, step=0.5, value=float(percentages.get("acrescimo_10_pecas", 0)))
        percentages["acrescimo_20_pecas_alto_atacado"] = col5.number_input("Acréscimo 20 peças - alto atacado (%)", min_value=0.0, step=0.5, value=float(percentages.get("acrescimo_20_pecas_alto_atacado", 0)))
        if markup_sequence_has_warning(percentages):
            st.warning("Atenção: normalmente o acréscimo diminui conforme a quantidade aumenta.")

    st.session_state["percentuais_acrescimo"] = percentages
    if percentages != previous:
        st.session_state["itens_orcamento"] = recalculate_quote_items(st.session_state["itens_orcamento"], percentages)
        _invalidate_quote()
    return percentages


def _render_product_search(percentages: dict) -> None:
    st.subheader("Busca de item")
    col_code, col_search = st.columns([3, 1])
    code = col_code.text_input(
        "Código do item",
        help="Digite o código completo, os 5 últimos dígitos ou pelo menos 4 números do código.",
        key="codigo_busca_produto",
    )
    normalized_code = normalize_product_code(code)
    search_clicked = col_search.button("Buscar item")
    if len(normalized_code) >= 4 or search_clicked:
        matches = search_products(st.session_state["base_produtos"], code)
        st.session_state["produtos_encontrados"] = matches
        if not matches:
            st.session_state["produto_encontrado"] = None
            st.error("Produto não encontrado na base importada.")
        elif len(matches) == 1:
            product = matches[0]
            st.session_state["produto_encontrado"] = product
            st.success("Produto encontrado.")
        else:
            st.session_state["produto_encontrado"] = None
    elif not normalized_code:
        st.session_state["produtos_encontrados"] = []
        st.session_state["produto_encontrado"] = None

    matches = st.session_state.get("produtos_encontrados") or []
    if len(matches) > 1:
        st.info("Foram encontrados vários produtos com esse código. Selecione o item correto.")
        selected_index = st.selectbox(
            "Produtos encontrados",
            options=list(range(len(matches))),
            format_func=lambda index: format_product_option(matches[index]),
            key="produto_ambiguo_selecionado",
        )
        product = matches[selected_index]
        st.session_state["produto_encontrado"] = product
    else:
        product = st.session_state.get("produto_encontrado")

    if not product:
        return

    if product.get("tem_divergencia"):
        st.warning("Produto encontrado em mais de um PDF com dados divergentes.")

    preview = create_quote_item(product, percentages)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Código": preview["produto"],
                    "Descrição": preview["descricao"],
                    "Peso": format_weight(preview["peso_g"]),
                    "Unidade": preview["unidade"],
                    "Classificação": preview["classificacao"],
                    "Avulso": format_brl(preview["preco_avulso"]),
                    "3 peças": format_brl(preview["preco_3_pecas"]),
                    "5 peças": format_brl(preview["preco_5_pecas"]),
                    "10 peças": format_brl(preview["preco_10_pecas"]),
                    "20 peças (alto atacado)": format_brl(preview["preco_20_pecas_alto_atacado"]),
                    "Observação": preview["observacao"],
                }
            ]
        ),
        width="stretch",
        hide_index=True,
    )

    if st.button("Adicionar ao orçamento"):
        st.session_state["itens_orcamento"].append(preview)
        _invalidate_quote()
        st.success("Item adicionado ao orçamento.")


def _render_quote_items(percentages: dict) -> None:
    st.subheader("Tabela de orçamento")
    items = st.session_state["itens_orcamento"]
    if not items:
        st.info("Nenhum item adicionado ao orçamento.")
        return

    df = pd.DataFrame(recalculate_quote_items(items, percentages))
    edited = st.data_editor(
        df[QUOTE_DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
        disabled=[column for column in QUOTE_DISPLAY_COLUMNS if column != "selecionar"],
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Selecionar"),
            "produto": st.column_config.TextColumn("Código do item"),
            "peso_g": st.column_config.NumberColumn("Peso", format="%.2f"),
            **_money_columns_config(),
        },
        key="quote_items_editor",
    )
    updated = df.copy()
    updated["selecionar"] = edited["selecionar"]
    records = updated.to_dict("records")
    if records != st.session_state["itens_orcamento"]:
        st.session_state["itens_orcamento"] = records
        _invalidate_quote()

    col_recalc, col_remove = st.columns(2)
    if col_recalc.button("Recalcular valores"):
        st.session_state["itens_orcamento"] = recalculate_quote_items(st.session_state["itens_orcamento"], percentages)
        _invalidate_quote()
        st.success("Valores recalculados.")
        st.rerun()
    if col_remove.button("Remover itens desmarcados"):
        st.session_state["itens_orcamento"] = [item for item in st.session_state["itens_orcamento"] if item.get("selecionar", True)]
        _invalidate_quote()
        st.rerun()

    totals = calculate_quote_totals(st.session_state["itens_orcamento"])
    st.metric("Total de modelos orçados", totals["total_modelos"])


def _render_quote_tab() -> None:
    if not st.session_state["extracao_confirmada"]:
        st.warning("Importe e confirme os PDFs antes de criar orçamentos ou pedidos.")
        return

    st.header("Orçamento")
    base = st.session_state["base_produtos"]
    st.caption(f"Base temporária: {len(base)} produto(s) disponível(is) para orçamento.")
    st.info("Os valores são calculados por métrica. No pedido, a métrica será aplicada conforme a quantidade total de itens selecionados.")

    company_data = _render_company_form()
    customer_data = _render_customer_form()
    company_data = _render_commercial_terms()
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
            items = recalculate_quote_items(st.session_state["itens_orcamento"], percentages)
            totals = calculate_quote_totals(items)
            quote_data = {
                "numero_orcamento": numero,
                "company_data": dict(company_data),
                "customer_data": dict(customer_data),
                "percentages": dict(percentages),
                "items": items,
                "totals": totals,
            }
            st.session_state["itens_orcamento"] = items
            st.session_state["numero_orcamento"] = numero
            st.session_state["orcamento_confirmado"] = True
            st.session_state["orcamento_em_edicao"] = False
            st.session_state["orcamento_confirmado_data"] = quote_data
            st.session_state["pdf_orcamento"] = build_quote_pdf(quote_data, _logo_bytes()).getvalue()
            _save_header_defaults(company_data, show_message=False)
            st.success(f"Orçamento {numero} confirmado.")

    if st.session_state["orcamento_confirmado"]:
        st.download_button(
            "Baixar PDF do orçamento",
            data=st.session_state["pdf_orcamento"],
            file_name=f"{st.session_state['numero_orcamento']}.pdf",
            mime="application/pdf",
        )
        if st.button("Gerar pedido"):
            if not st.session_state.get("orcamento_confirmado") or not st.session_state.get("orcamento_confirmado_data"):
                st.warning("Confirme o orçamento antes de gerar o pedido.")
                return

            quote_data = st.session_state["orcamento_confirmado_data"]
            st.session_state["itens_pedido"] = recalculate_order_items(create_order_from_quote(quote_data), quote_data["percentages"])
            st.session_state["orcamento_confirmado"] = True
            st.session_state["orcamento_em_edicao"] = False
            st.session_state["pedido_em_edicao"] = True
            st.session_state["pedido_confirmado"] = False
            st.session_state["pedido_confirmado_data"] = None
            st.session_state["pedido_quantidades_confirmadas"] = True
            st.session_state["pedido_tem_alteracao_pendente"] = False
            st.session_state["pdf_pedido"] = None
            st.session_state["active_page"] = "Pedido"
            st.rerun()
    elif st.session_state["numero_orcamento"] or st.session_state["orcamento_em_edicao"]:
        st.warning("Orçamento em edição. Confirme novamente para gerar PDF ou pedido atualizado.")

    _render_edit_quote_button("orcamento")


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
    st.info("A métrica aplicada é calculada pela quantidade total do pedido, não pela quantidade individual de cada item.")

    if not st.session_state["itens_pedido"]:
        st.session_state["itens_pedido"] = recalculate_order_items(create_order_from_quote(quote_data), quote_data["percentages"])

    if any(column not in item for item in st.session_state["itens_pedido"] for column in ORDER_DISPLAY_COLUMNS):
        st.session_state["itens_pedido"] = recalculate_order_items(st.session_state["itens_pedido"], quote_data["percentages"])

    items = st.session_state["itens_pedido"]
    df = pd.DataFrame(items)
    edited = st.data_editor(
        df[ORDER_DISPLAY_COLUMNS],
        width="stretch",
        hide_index=True,
        disabled=["produto", "descricao", "unidade", "metrica_aplicada", "preco_unitario", "valor_total", "valor_se_avulso", "observacao"],
        column_config={
            "selecionar": st.column_config.CheckboxColumn("Selecionar"),
            "produto": st.column_config.TextColumn("Código"),
            "quantidade": st.column_config.NumberColumn("Quantidade", min_value=1, step=1),
            **_money_columns_config(),
        },
        key="order_items_editor",
    )

    edited_records = df.to_dict("records")
    quantity_changed = False
    selection_changed = False
    for index, record in enumerate(edited_records):
        new_quantity = int(edited.iloc[index]["quantidade"] or 0)
        new_selected = bool(edited.iloc[index]["selecionar"])
        if new_quantity != int(record.get("quantidade") or 0):
            quantity_changed = True
            record["quantidade"] = new_quantity
        if new_selected != bool(record.get("selecionar")):
            selection_changed = True
            record["selecionar"] = new_selected

    if quantity_changed:
        st.session_state["itens_pedido"] = edited_records
        st.session_state["pedido_tem_alteracao_pendente"] = True
        st.session_state["pedido_quantidades_confirmadas"] = False
        st.session_state["pedido_confirmado"] = False
        st.session_state["pdf_pedido"] = None
        st.warning("Você alterou quantidades do pedido. Confirme as alterações para continuar.")
    elif selection_changed:
        st.session_state["itens_pedido"] = recalculate_order_items(edited_records, quote_data["percentages"])
        st.session_state["pedido_confirmado"] = False
        st.session_state["pdf_pedido"] = None

    col_confirm_qty, col_recalc, col_back = st.columns(3)
    if col_confirm_qty.button("Confirmar alterações de quantidade", disabled=not st.session_state["pedido_tem_alteracao_pendente"]):
        st.session_state["itens_pedido"] = recalculate_order_items(st.session_state["itens_pedido"], quote_data["percentages"])
        st.session_state["pedido_tem_alteracao_pendente"] = False
        st.session_state["pedido_quantidades_confirmadas"] = True
        st.session_state["pedido_confirmado"] = False
        st.session_state["pdf_pedido"] = None
        st.success("Alterações de quantidade confirmadas.")
        st.rerun()

    if col_recalc.button("Recalcular pedido"):
        st.session_state["itens_pedido"] = recalculate_order_items(st.session_state["itens_pedido"], quote_data["percentages"])
        if st.session_state["pedido_tem_alteracao_pendente"]:
            st.info("Recalculei os valores, mas ainda é necessário confirmar as alterações de quantidade.")
        else:
            st.success("Pedido recalculado.")
        st.session_state["pedido_confirmado"] = False
        st.session_state["pdf_pedido"] = None
        st.rerun()

    if col_back.button("Voltar para orçamento"):
        st.session_state["active_page"] = "Orçamento"
        st.rerun()

    if st.session_state["pedido_tem_alteracao_pendente"]:
        st.warning("Você alterou quantidades do pedido. Confirme as alterações para continuar.")

    totals = calculate_order_totals(st.session_state["itens_pedido"])
    col_qty, col_avulso, col_total = st.columns(3)
    col_qty.metric("Quantidade total do pedido", totals["quantidade_total"])
    col_avulso.metric("Valor total avulso", format_brl(totals.get("valor_total_avulso", 0)))
    col_total.metric("Valor total do pedido", format_brl(totals["valor_total"]))
    st.metric("Métrica aplicada ao pedido", totals.get("metrica_aplicada") or "-")

    blocked_by_quantity = st.session_state["pedido_tem_alteracao_pendente"] or not st.session_state["pedido_quantidades_confirmadas"]
    if st.button("Confirmar pedido", type="primary", disabled=blocked_by_quantity):
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
            st.session_state["pedido_em_edicao"] = False
            st.session_state["pedido_confirmado"] = True
            st.session_state["pedido_confirmado_data"] = order_data
            st.session_state["pdf_pedido"] = build_order_pdf(order_data, _logo_bytes()).getvalue()
            _save_header_defaults(quote_data.get("company_data", {}), show_message=False)
            st.success(f"Pedido {order_data['numero_pedido']} confirmado.")

    if blocked_by_quantity:
        st.info("Confirme as alterações de quantidade para liberar a confirmação e o PDF do pedido.")

    if st.session_state["pedido_confirmado"] and not blocked_by_quantity:
        st.download_button(
            "Baixar PDF do pedido",
            data=st.session_state["pdf_pedido"],
            file_name=f"{st.session_state['numero_pedido']}.pdf",
            mime="application/pdf",
        )

    _render_edit_quote_button("pedido")


_init_state()

st.title("Extrator de Itens de Pedido de Venda")

PAGES = ["Importar PDFs", "Orçamento", "Pedido"]
if st.session_state.get("active_page") not in PAGES:
    st.session_state["active_page"] = "Importar PDFs"

selected_page = st.radio(
    "Navegação",
    PAGES,
    index=PAGES.index(st.session_state["active_page"]),
    horizontal=True,
)
st.session_state["active_page"] = selected_page

if selected_page == "Importar PDFs":
    _render_import_tab()
elif selected_page == "Orçamento":
    _render_quote_tab()
elif selected_page == "Pedido":
    _render_order_tab()

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.excel_writer import build_excel
from src.extractor import extract_pdf
from src.models import ITEM_COLUMNS, SUMMARY_COLUMNS


st.set_page_config(page_title="Extrator de Itens de Pedido de Venda", layout="wide")


def _empty_dataframes() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.DataFrame(columns=ITEM_COLUMNS), pd.DataFrame(columns=SUMMARY_COLUMNS)


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


st.title("Extrator de Itens de Pedido de Venda")

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

if "items_df" not in st.session_state:
    st.session_state["items_df"], st.session_state["summary_df"] = _empty_dataframes()
    st.session_state["warnings"] = []

items_df = st.session_state["items_df"]
summary_df = st.session_state["summary_df"]
warnings = st.session_state["warnings"]

if not summary_df.empty:
    st.subheader("Resumo do processamento")
    st.metric("PDFs selecionados", len(summary_df))
    st.metric("Total de linhas processadas", int(summary_df["linhas_extraidas"].sum()))

    st.dataframe(summary_df, use_container_width=True, hide_index=True)

    divergent = summary_df[summary_df["status_pdf"].eq("DIVERGENTE")]
    not_found = summary_df[summary_df["status_pdf"].eq("NÃO ENCONTRADO")]
    errored = summary_df[summary_df["status_pdf"].eq("ERRO")]

    if not divergent.empty:
        st.error("Há PDFs com quantidade de itens divergente. Confira o resumo antes de gerar a planilha.")

    if not_found.empty is False:
        st.warning("Há PDFs sem a informação 'Itens:' no rodapé.")

    if errored.empty is False:
        st.error("Há PDFs que não puderam ser processados. Confira as observações no resumo.")

    for warning in warnings:
        st.warning(warning)

    st.subheader("Prévia dos itens extraídos")
    if items_df.empty:
        st.info("Nenhuma linha de item foi extraída dos PDFs selecionados.")
    else:
        st.dataframe(items_df, use_container_width=True, hide_index=True)

    confirmed = st.checkbox("Conferi a prévia e confirmo a geração da planilha Excel")

    if confirmed:
        excel_data = st.session_state.get("excel_data") or build_excel(items_df, summary_df)
        st.download_button(
            "Baixar Excel",
            data=excel_data,
            file_name="itens_pedido_venda.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedItem:
    arquivo_origem: str
    numero_pedido: str
    produto: str
    descricao: str
    pagina: int
    linha_original: str


@dataclass(slots=True)
class PdfSummary:
    arquivo_origem: str
    numero_pedido: str
    linhas_extraidas: int
    status_pdf: str


ITEM_COLUMNS = [
    "arquivo_origem",
    "numero_pedido",
    "faturamento",
    "cliente",
    "cpf_cnpj",
    "vendedor",
    "tipo_pagamento",
    "condicao_pagamento",
    "classificacao",
    "valor_grama_classificacao",
    "produto",
    "descricao",
    "peso_g",
    "quantidade",
    "unidade",
    "valor_base",
    "percentual",
    "valor_unitario",
    "valor_total",
    "confianca_extracao",
    "status_conferencia",
    "observacao",
    "pagina",
    "linha_original",
]

SUMMARY_COLUMNS = [
    "arquivo_origem",
    "numero_pedido",
    "cliente",
    "faturamento",
    "linhas_extraidas",
    "linhas_ok",
    "linhas_conferir",
    "itens_rodape",
    "status_pdf",
    "observacoes_pdf",
]

IGNORED_PREFIXES = (
    "PEDIDO DE VENDA",
    "NUMERO:",
    "NÚMERO:",
    "FATURAMENTO:",
    "CLIENTE:",
    "CPF/CNPJ:",
    "ENDERECO:",
    "ENDEREÇO:",
    "BAIRRO:",
    "MUNICIPIO:",
    "MUNICÍPIO:",
    "CEP:",
    "VENDEDOR:",
    "TIPO.PAG.:",
    "COND.PAG.:",
    "FOTO PRODUTO",
    "CLASSIFICACAO:",
    "CLASSIFICAÇÃO:",
    "TOTAL CLASSIFICACAO",
    "TOTAL CLASSIFICAÇÃO",
    "ITENS:",
    "OBSERVACOES",
    "OBSERVAÇÕES",
    "FRETE:",
    "FORMA ENVIO",
    "OUTROS:",
    "VALOR TOTAL:",
    "FORMA DE PAGAMENTO",
    "DOCUMENTO FORMA",
    "DEV-",
)

COMMON_UNITS = {
    "UN",
    "PR",
    "CJ",
    "PC",
    "PÇ",
    "PT",
    "CX",
    "KIT",
    "PAR",
}

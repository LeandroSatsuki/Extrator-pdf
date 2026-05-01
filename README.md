# Extrator-pdf

Aplicativo web local para extrair itens de PDFs de Pedido de Venda com layout padronizado. O sistema lê PDFs pesquisáveis, extrai cabeçalho e itens, calcula confiança por linha, mostra uma prévia para conferência e gera uma planilha Excel com as abas `Itens` e `Resumo`.

O projeto não usa OCR inicialmente. Se um PDF não tiver texto extraível, ele é marcado como erro e o app informa: `PDF sem texto pesquisável. Possivelmente escaneado. Necessário OCR.`

## Requisitos

- Python 3.11 ou superior
- Streamlit
- pdfplumber
- pandas
- openpyxl

## Instalação

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Como rodar

```powershell
streamlit run app.py
```

Depois de executar o comando, abra a URL local exibida pelo Streamlit no navegador.

## Como usar

1. Selecione até 5 arquivos PDF.
2. Clique em `Processar PDFs`.
3. Confira o resumo por PDF e os alertas.
4. Confira a prévia dos itens extraídos.
5. Marque `Conferi a prévia e confirmo a geração da planilha Excel`.
6. Clique em `Baixar Excel`.

Se mais de 5 PDFs forem selecionados, o processamento é bloqueado com a mensagem `Selecione no máximo 5 arquivos PDF.`

## Colunas da aba Itens

- `arquivo_origem`
- `numero_pedido`
- `faturamento`
- `cliente`
- `cpf_cnpj`
- `vendedor`
- `tipo_pagamento`
- `condicao_pagamento`
- `classificacao`
- `valor_grama_classificacao`
- `produto`
- `descricao`
- `peso_g`
- `quantidade`
- `unidade`
- `valor_base`
- `percentual`
- `valor_unitario`
- `valor_total`
- `confianca_extracao`
- `status_conferencia`
- `observacao`
- `pagina`
- `linha_original`

## Colunas da aba Resumo

- `arquivo_origem`
- `numero_pedido`
- `cliente`
- `faturamento`
- `linhas_extraidas`
- `linhas_ok`
- `linhas_conferir`
- `itens_rodape`
- `status_pdf`
- `observacoes_pdf`

## Confiança da extração

Cada item recebe uma pontuação de 0 a 100:

- Regex completa bateu exatamente: 40 pontos
- Produto numérico com 8 a 12 dígitos: 10 pontos
- Peso válido e maior que zero: 10 pontos
- Quantidade válida e maior que zero: 10 pontos
- Unidade reconhecida: 5 pontos
- Valores monetários convertidos: 10 pontos
- Valor total confere com quantidade x valor unitário, com tolerância de R$ 0,02: 10 pontos
- Classificação identificada: 5 pontos

Linhas com confiança maior ou igual a 90 ficam como `OK`. Linhas abaixo de 90 permanecem na planilha como `CONFERIR` com observação objetiva.

## Validação por PDF

O app procura o campo `Itens:` no texto completo do PDF e compara esse valor com a quantidade de linhas extraídas:

- `OK`: quantidade extraída igual ao rodapé.
- `DIVERGENTE`: quantidade extraída diferente do rodapé.
- `NÃO ENCONTRADO`: campo `Itens:` não encontrado.
- `ERRO`: PDF sem texto pesquisável ou erro de leitura.

## Observações técnicas

- A extração é determinística, baseada em regex e validações.
- O app ignora cabeçalhos, totais, rodapé, forma de pagamento e parcelas.
- A coluna `linha_original` preserva o texto extraído para auditoria.
- Não são inventados campos ausentes.

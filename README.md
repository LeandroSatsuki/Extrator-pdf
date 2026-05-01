# Extrator-pdf

Aplicativo web local em Python para extrair itens de PDFs de Pedido de Venda, consolidar uma base temporária de produtos, montar orçamentos por métricas de preço, gerar pedidos por quantidade e baixar arquivos Excel/PDF.

O app usa extração determinística com `pdfplumber`, regex e validações. Não usa OCR, banco de dados, APIs externas ou IA para interpretar campos.

## Funcionalidades

- Importação de até 5 PDFs por processamento.
- Extração de cabeçalho e itens da tabela de Pedido de Venda.
- Validação por rodapé com o campo `Itens:`.
- Cálculo de confiança por linha extraída.
- Excel com abas `Itens` e `Resumo`.
- Base temporária de produtos consolidada por código.
- Orçamento por métricas: `Avulso`, `2 a 4`, `5 a 7`, `8 a 19`, `Acima de 20`.
- Acréscimos configuráveis sobre o custo da base.
- PDF de orçamento com tabela por métrica, sem quantidade.
- Pedido gerado a partir do orçamento, com quantidade, métrica aplicada e total.
- Confirmação obrigatória quando quantidades do pedido forem alteradas.
- PDF de pedido com total geral e assinaturas.
- Logo fixa em `assets/logo.png` com opção de upload temporário.
- Dados da empresa/vendedor e condições comerciais podem ser salvos como padrão local.
- Edição/refazer orçamento sem apagar os dados atuais.

## Requisitos

- Python 3.11 ou superior
- Streamlit
- pdfplumber
- pandas
- openpyxl
- reportlab

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

## Logo fixa

Para deixar uma logo fixa no sistema, coloque o arquivo em:

```text
assets/logo.png
```

Se esse arquivo existir, ele será usado automaticamente nos PDFs de orçamento e pedido. Na aba Orçamento, ainda é possível enviar outra logo temporariamente para substituir a logo fixa durante o uso.

## Dados padrão do cabeçalho

Os dados da empresa/vendedor e as condições comerciais podem ser salvos como padrão pelo botão `Salvar dados do cabeçalho como padrão`.

O app também salva esses dados automaticamente ao confirmar um orçamento ou um pedido. O arquivo local usado é:

```text
data/last_header_data.json
```

Esse arquivo não é enviado para o GitHub. Os dados do cliente nunca são salvos como padrão e devem ser preenchidos a cada novo orçamento.

Para limpar os dados padrão, apague:

```text
data/last_header_data.json
```

## Aba Importar PDFs

1. Selecione até 5 PDFs.
2. Clique em `Processar PDFs`.
3. Confira o resumo por PDF e a prévia dos itens.
4. Marque `Conferi a prévia e confirmo a geração da planilha Excel`.
5. Clique em `Confirmar extração`.
6. Baixe o Excel, se desejar.

Após confirmar a extração, os itens viram uma base temporária de produtos para orçamento e pedido.

## Aba Orçamento

Os campos de cabeçalho ficam em seções minimizáveis:

- Dados da empresa / vendedor
- Dados do cliente
- Condições comerciais
- Percentuais de acréscimo

O orçamento não usa quantidade. Ele apresenta uma tabela de preços por métrica/faixa.

Para adicionar item:

1. Digite o código do item.
2. Clique em `Buscar item`.
3. Confira descrição, peso, unidade, classificação, custo base e preços calculados.
4. Clique em `Adicionar ao orçamento`.

As métricas do orçamento são:

- Avulso
- 2 a 4
- 5 a 7
- 8 a 19
- Acima de 20

Os percentuais são acréscimos sobre o custo da base, não descontos. O custo usa preferencialmente `valor_unitario_original`; se ausente, usa `valor_base_original`.

Fórmula:

```text
preço da métrica = valor_custo_base * (1 + percentual_acrescimo / 100)
```

Se uma faixa maior tiver acréscimo maior que a faixa anterior, o app mostra o aviso:

```text
Atenção: normalmente o acréscimo diminui conforme a quantidade aumenta.
```

Esse aviso não bloqueia o orçamento.

## PDF do orçamento

O PDF mostra:

- Logo no topo, se existir.
- Dados da empresa e do cliente em dois blocos lado a lado.
- Detalhes do orçamento em bloco próprio abaixo do cabeçalho.
- Tabela com Código, Descrição, Avulso, 2 a 4, 5 a 7, 8 a 19, Acima de 20.
- Total de modelos orçados.

O PDF do orçamento não mostra quantidade, preço aplicado nem valor total geral.

## Aba Pedido

O pedido só fica disponível após confirmar o orçamento.

Na tabela do pedido:

- Selecione os itens.
- Informe ou altere a quantidade.
- O sistema aplica automaticamente a métrica correta:
  - quantidade 1: Avulso
  - 2 a 4: preço 2 a 4
  - 5 a 7: preço 5 a 7
  - 8 a 19: preço 8 a 19
  - 20 ou mais: Acima de 20

Se qualquer quantidade for alterada, o app bloqueia a confirmação e o PDF do pedido até clicar em `Confirmar alterações de quantidade`.

## Editar orçamento

O botão `Editar orçamento / Refazer orçamento` não apaga dados. Ele apenas libera o orçamento atual para edição, mantém itens, cliente, empresa, logo e percentuais, invalida o PDF antigo e exige nova confirmação antes de gerar PDF ou pedido atualizado.

## Excel

A planilha gerada possui abas:

- `Itens`
- `Resumo`

O cabeçalho das duas abas tem fundo escuro, fonte branca, negrito, filtro automático e primeira linha congelada.

## Observações técnicas

- Produtos duplicados são consolidados por código.
- Se o mesmo código aparecer com descrição, peso ou valor divergente, o primeiro registro é mantido e o produto recebe observação de divergência.
- PDFs escaneados ou sem texto pesquisável são sinalizados como erro; OCR não é executado nesta etapa.

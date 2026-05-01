# Extrator-pdf

Aplicativo web local em Python para extrair itens de PDFs de Pedido de Venda, consolidar uma base temporária de produtos, criar orçamentos comerciais, gerar pedidos e baixar arquivos Excel/PDF.

O app usa extração determinística com `pdfplumber`, regex e validações. Não usa OCR, banco de dados, APIs externas ou IA para interpretar campos. Se um PDF não tiver texto pesquisável, ele é marcado como erro e o usuário é avisado de que OCR será necessário futuramente.

## Funcionalidades

- Importação de até 5 PDFs por processamento.
- Extração de cabeçalho e itens da tabela de Pedido de Venda.
- Validação por rodapé com o campo `Itens:`.
- Cálculo de confiança por linha extraída.
- Geração de Excel com abas `Itens` e `Resumo`.
- Consolidação dos itens extraídos em uma base temporária de produtos.
- Criação de orçamento por busca de código de produto.
- Percentuais de acréscimo por faixa de quantidade.
- PDF de orçamento com logo opcional.
- Geração de pedido a partir do orçamento confirmado.
- Seleção e ajuste de itens no pedido.
- PDF de pedido com logo opcional e campos de assinatura.
- Opção de refazer orçamento mantendo base importada, dados da empresa, logo e percentuais.

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

## Aba Importar PDFs

1. Selecione até 5 PDFs.
2. Clique em `Processar PDFs`.
3. Confira o resumo por PDF e a prévia dos itens.
4. Marque `Conferi a prévia e confirmo a geração da planilha Excel`.
5. Clique em `Confirmar extração`.
6. Baixe o Excel, se desejar.

Após confirmar a extração, os itens viram uma base temporária de produtos para orçamento e pedido.

## Aba Orçamento

Preencha os dados da empresa/vendedor, faça upload opcional da logo, informe os dados do cliente e configure os percentuais:

- Acréscimo 1 a 3 unidades
- Acréscimo 4 a 6 unidades
- Acréscimo 7 a 9 unidades
- Acréscimo acima de 10 unidades

Para adicionar item:

1. Digite o código do produto.
2. Informe a quantidade desejada.
3. Clique em `Buscar item`.
4. Confira descrição, peso, unidade, classificação e preços por faixa.
5. Clique em `Adicionar item`.

O preço aplicado é escolhido automaticamente pela quantidade:

- 1 a 3 unidades: preço 1 a 3
- 4 a 6 unidades: preço 4 a 6
- 7 a 9 unidades: preço 7 a 9
- 10 ou mais unidades: preço acima de 10

Depois de revisar, clique em `Confirmar orçamento`. O PDF do orçamento fica disponível para download. Se percentuais ou itens forem alterados depois da confirmação, o orçamento precisa ser confirmado novamente.

## Aba Pedido

A aba Pedido exige um orçamento confirmado.

1. Gere o pedido a partir do orçamento.
2. Selecione os itens que entrarão no pedido.
3. Ajuste a quantidade final, se necessário.
4. Clique em `Recalcular pedido`.
5. Clique em `Confirmar pedido`.
6. Baixe o PDF do pedido.

Se a quantidade do pedido mudar, o preço aplicado é recalculado usando os mesmos percentuais do orçamento.

## Refazer orçamento

Use `Refazer orçamento` para limpar:

- Dados do cliente
- Itens do orçamento
- Orçamento confirmado
- Pedido gerado

São mantidos:

- Base de produtos importada dos PDFs
- Dados da empresa/vendedor
- Logo carregada
- Percentuais de acréscimo

Antes de limpar, marque `Confirmo que desejo refazer o orçamento`.

## Colunas do Excel

A aba `Itens` contém os dados extraídos dos PDFs, incluindo `linha_original` e `pagina` para auditoria.

A aba `Resumo` contém arquivo de origem, número do pedido, cliente, faturamento, linhas extraídas, linhas OK, linhas para conferir, itens do rodapé, status do PDF e observações.

## Confiança da extração

Cada linha recebe pontuação de 0 a 100:

- Regex completa: 40 pontos
- Produto numérico com 8 a 12 dígitos: 10 pontos
- Peso válido: 10 pontos
- Quantidade válida: 10 pontos
- Unidade reconhecida: 5 pontos
- Valores monetários convertidos: 10 pontos
- Total confere com quantidade x valor unitário: 10 pontos
- Classificação identificada: 5 pontos

Linhas com confiança maior ou igual a 90 ficam como `OK`. Linhas abaixo de 90 permanecem no Excel como `CONFERIR` com observação.

## Observações

- O valor original extraído do PDF é usado como base interna de cálculo.
- O app não inventa dados ausentes.
- Produtos duplicados são consolidados por código.
- Se o mesmo código aparecer com descrição, peso ou valor divergente, o primeiro registro é mantido e o produto recebe observação de divergência.

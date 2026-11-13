# Conjunto de PDFs para comparação pdf_loader × Docling

Prova do B04b: a regra de aceite do v1-5 diz que o Docling substitui o
pdf_loader como padrão se perder menos provas do gabarito, reduzir cabeçalhos
e rodapés restantes e tiver tempo aceitável.

## Como usar

1. Coloque de 3 a 5 PDFs de diagramação variada em `data/raw/`
   (romance, notícia em colunas, relatório com tabelas, PDF escaneado etc.).
   Os PDFs **não** entram no Git — só este manifesto.
2. Liste os nomes dos arquivos em `conjunto.txt`, um por linha, com um
   comentário dizendo o que cada um exercita.
3. Rode `make compare-all`. Para um PDF só: `make compare PDF=<nome>`.

Cada comparação fica em `data/processed/<hash>/comparacao_docling.md`, com:
títulos, subtítulos, sumário/folha de rosto, cabeçalhos restantes no canônico
e parágrafos que atravessam página.

## O que observar na revisão

- Títulos que o Docling encontra e o pdf_loader perde (e vice-versa).
- Subtítulos colados ao primeiro parágrafo no pdf_loader.
- Itens de folha de rosto/sumário que viraram texto.
- Cabeçalhos que a remoção por repetição não pegou.
- Parágrafos que atravessam página sem hífen (o pdf_loader divide em dois).

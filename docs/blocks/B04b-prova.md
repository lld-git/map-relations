# B04b-prova — Correções genéricas no canônico e prova do Docling
Commits: 2a23109 (código), docs no commit seguinte
Data: 2026-11-12

## Relatório de conclusão (verbatim)

**B04b-prova concluído** — 149 testes, `make check` e `make map` verdes. O Processo saiu de 24 "capítulos" errados para **10 corretos (1–10)**. A comparação com o Docling rodou ponta a ponta. Parado para sua revisão.

**1. Correções genéricas no canonical.py** (nenhuma regra específica de livro):
- **Letras espaçadas**: a detecção de título testa também a forma sem espaços quando a maioria dos tokens tem 1 caractere — "C A P Í T U L O I" casa o padrão explícito.
- **Numeração só dentro da obra**: se existem títulos explícitos (Capítulo N, romanos), só eles numeram capítulos; folha de rosto, sinopse e subtítulos em maiúsculas viram parágrafos de texto, cada um com alerta. Sem nenhum explícito, a regra de maiúsculas numera — com alerta pedindo confirmação.
- **Alertas novos**: capítulo sem parágrafos de texto; títulos detectados só por maiúsculas.
- Resultado no O Processo: cap. 1 = Capítulo I; folha de rosto e sinopse no preâmbulo; subtítulos ("NA CATEDRAL", "O VERDUGO"…) preservados como texto do capítulo certo. O hash do canônico não mudou (classificação não altera o texto).

**2. Prova do Docling**: imagem real em docker/docling/Dockerfile (modelos baixados no build, `DOCLING_ARTIFACTS_PATH`), serviço no profile `docling`. `make compare PDF=x` converte com o Docling e gera `data/processed/<hash>/comparacao_docling.md` com: títulos explícitos (casando com os capítulos do pdf_loader), subtítulos, folha de rosto/sumário, cabeçalhos restantes no canônico e parágrafos que atravessam página — incerteza marcada com "?".

**Resultado na fatia de 40 páginas** (61 s, ~1,5 s/página, sem OCR):
- Títulos explícitos: pdf_loader 1 × Docling **0** — o Docling rotulou "C A P Í T U L O I" como texto comum, não como section_header. Ponto contra o Docling nesse PDF.
- Blocos de texto: 43 × **125** — o pdf_loader cola parágrafos (página sem linha em branco vira um bloco só); o Docling segmenta muito melhor. Ponto forte do Docling.
- Cabeçalhos/rodapés: 37 removidos por repetição × **0** rotulados pelo Docling — a heurística de repetição cobriu tudo o que o Docling veria, e o Docling não marcou nada neste PDF.
- 1 parágrafo atravessando página detectado pelo Docling (o pdf_loader divide esses em dois).

**Limitação encontrada**: com 379 páginas o Docling morre por **OOM** na VM do Docker Desktop (3,7 GiB), mesmo com `--page-batch-size 1`. A prova rodou numa fatia de 40 páginas (`data/raw/o_processo_p1-40.pdf`, gerada com pypdf, fora do Git). **Ação sua**: subir a memória da VM (Settings → Resources, sugiro 8 GiB) para rodar o livro inteiro.

**3. eval/pdfs/**: manifesto `conjunto.txt` (o_processo.pdf já listado; espaços para os seus 3–5 PDFs variados) + README com o que observar. `make compare-all` roda a comparação de todos os listados.

**Pontos para sua revisão:**
1. A precedência "explícito > maiúsculas" assume que obras com capítulos numerados os marcam de forma explícita — nos seus PDFs variados isso será testado pelo `compare-all`.
2. O resultado preliminar sugere a divisão natural do B04b: Docling para segmentação de parágrafos, heurística de repetição mantida para cabeçalhos. A decisão final fica para a regra de aceite com gabarito.
3. Subtítulo em caixa mista grudado no 1º parágrafo ("Prisão. Conversa…"): continua sem solução genérica no pdf_loader; o Docling o separa (125 blocos) — mais um argumento para o B04b.

## Revisão humana

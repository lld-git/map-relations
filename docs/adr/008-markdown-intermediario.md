# ADR 008 — Markdown estruturado como formato intermediário único da ingestão

**Data:** 2026-11-12  
**Status:** aceito (revisado pelo Leon em 2026-11-12)

## Contexto

Hoje cada parser (pdf_loader; DoclingParser planejado; TXT/EPUB pendentes)
teria que produzir IngestResult diretamente, duplicando segmentação, detecção
de capítulos e alertas por formato. A prova do B04b (comparacao_docling.md da
fatia de 40 páginas) mostrou que o Docling segmenta parágrafos muito melhor
(125 blocos × 43 do pdf_loader), mas perde títulos com letras espaçadas e é
caro: ~1,5 s/página na CPU e OOM com 379 páginas em VM de 3,7 GiB. Além
disso, a delimitação da obra (v1-5) exige revisão humana, e não há hoje um
artefato natural para o humano editar.

## Proposta

### 1. Conversores por formato → documento.md + pages.json

| Formato | Conversor | Observação |
|---|---|---|
| PDF | Docling (padrão) | via cache docling.json; ver §4 |
| PDF | pdf_loader (fallback) | rota barata; grava pdf_loader/raw.json |
| EPUB, DOCX, HTML | pandoc | contêiner próprio ou na imagem dev |
| TXT | direto | só normalização |

O conversor é o único código que conhece o formato de origem. Tudo depois
dele opera sobre documento.md.

### 2. Convenção do Markdown (subconjunto restrito)

- `# Título` — título de capítulo (um `#` só).
- Linha inteira em itálico (`*...*`) imediatamente após o título — subtítulo.
- Parágrafos separados por linha em branco.
- Sem cabeçalhos nem rodapés de página (removidos pelo conversor).
- Todo o resto é texto literal: o parser único NÃO interpreta Markdown
  completo. Caracteres especiais do Markdown vindos do documento são
  escapados pelo conversor e des-escapados pelo parser (Princípio 8:
  texto de documento é dado, nunca instrução).

### 3. Parser único → IngestResult

Um só parser transforma documento.md em IngestResult: texto canônico sem
marcação, offsets em code points NFC (ADR 004), parágrafos, capítulos,
subtítulos e QualityReport. Mantém-se um mapa de posições canônico ↔ Markdown
para a revisão apontar de volta ao .md.

### 4. Cache do Docling

- O Docling roda **uma vez por documento** e grava docling.json.
- Chave de cache: hash do PDF + versão do Docling + opções de conversão.
- documento.md é **sempre** gerado a partir do docling.json, nunca do PDF.
- Para PDF com camada de texto: OCR, tabelas e imagens **desligados**.
- Medir tempo e memória antes e depois dessas opções (mesma fatia de
  40 páginas; `/usr/bin/time -v` no contêiner) e registrar aqui.

### 5. Layout de data/processed/ (uma pasta por hash do PDF)

```
data/processed/<hash_pdf>/
  source.json                      nome do arquivo, páginas, hash do PDF
  docling/<versao>-<opcoes>/docling.json   cache da conversão cara
  pdf_loader/raw.json              rota alternativa, se usada
  documento.md                     FONTE, revisada pelo humano
  pages.json                       mapa de páginas do documento.md
  canonical.txt                    derivado do .md
  ingest.json                      derivado: parágrafos, capítulos, hash canônico
  report.md                        revisão da ingestão
  comparacao_docling.md            comparação entre rotas
```

- O hash canônico fica **dentro** de ingest.json; o nome da pasta usa o hash
  do PDF (estável mesmo quando o pipeline muda).
- Comando de limpeza (`make clean-processed` ou subcomando da CLI) remove
  pastas órfãs: hash de PDF que não existe mais em data/raw/ e caches
  docling/<versao>-<opcoes>/ de versões antigas.

### 6. Revisão humana e fim do corpus.yaml

O humano edita documento.md diretamente (apagar paratexto, corrigir título,
delimitar a obra). Não há corpus.yaml: o próprio .md é a fonte revisada.

**Regra de integridade:** qualquer edição em documento.md muda o hash
canônico e invalida os derivados — canonical.txt, ingest.json e qualquer
offset (gabarito, evidências) referem-se sempre a um hash canônico
específico. Reprocessar depois de editar é obrigatório e barato (parser
único, sem Docling).

## Impacto no código atual

| Peça | Destino |
|---|---|
| `canonical.py: _clean_pages, _join_pages, _find_repeated_edges` | ficam na rota pdf_loader (viram parte do conversor fallback) |
| `canonical.py: _is_explicit_heading, _despace, precedência, alertas` | reaproveitados no conversor (decidir o que vira `#`) |
| `canonical.py: montagem de parágrafos/capítulos/offsets` | reaproveitada no parser único (entrada passa a ser blocos do .md) |
| `core/ingest_contract.py` (IngestResult, locate) | **inalterado**; avaliar campo opcional para subtítulo e páginas |
| `ingest/report.py`, `docling_compare.py` | inalterados na essência; caminhos novos |
| CLI `ingest` / `compare` | passam a orquestrar conversor → .md → parser |
| Testes de contrato, locate, offsets | **inalterados** |
| Testes de limpeza de página | movem para a rota pdf_loader |
| Testes novos | convenção do .md, escape, parser único, cache, limpeza de órfãos |

## Questões decididas na revisão (Leon, 2026-11-12)

1. **Mapa de páginas**: marcadores de página como comentários HTML no próprio
   .md (`<!-- p.12 -->`). Sobrevivem à edição humana e são removidos pelo
   parser antes do canônico; pages.json deixa de ser arquivo separado.
2. **Subtítulo no contrato**: criar `ParagraphKind.subtitulo` para a linha em
   itálico após o título.
3. **pandoc**: entra na imagem dev (leve, sem modelos); não ganha serviço.

**Regra de ordem no B02 (confirmada):** revisar documento.md ANTES de
preencher o gabarito. Editar o .md muda o hash canônico e invalida qualquer
offset já registrado (gabarito, evidências).

## Pendente futuro (registrado, nada agora)

Materiais com **tabelas ou imagens** precisarão de revisão desta decisão
(hoje a conversão as desliga). No produto, o usuário deve poder informar em
caixas de seleção o que o material contém e o que deseja extrair (texto,
tabelas, imagens) — as opções de conversão derivam dessa escolha, e a chave
de cache (§4) já comporta isso por incluir as opções.

## Consequências esperadas

- Docling roda 1× por documento; todo reprocessamento posterior é barato.
- Revisão humana ganha um artefato editável e versionável por hash.
- Um parser único testado substitui N caminhos de segmentação.
- O comparativo pdf_loader × Docling passa a ser entre dois geradores de
  documento.md, com o mesmo parser — comparação mais justa.

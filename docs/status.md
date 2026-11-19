# Status — atualizado em 2026-11-19

Ordem dos blocos: B04 foi antecipado antes do B02 (decisão do Leon em
2026-11-11), porque os offsets do gabarito referenciam o texto canônico.
Ordem atual: B00 → B00b → B01 → **B04** → B02 → B02b → B03 → B04 (TXT/EPUB) → B04b → B05…

## Concluído

- **B01b** — relações simétricas: `RelationType.symmetric`, `claim_key` ordena
  sujeito/objeto quando simétrico; ADR 003 e schema atualizados; 3 novos testes.
  Relatório: [docs/blocks/B01b.md](blocks/B01b.md).
- **B00** — fundação: projeto Python (uv), pytest, ruff, mypy, CI.
  Relatório: [docs/blocks/B00.md](blocks/B00.md).
- **B00b** — Docker: multi-stage prod/dev, compose (app, painel em
  127.0.0.1:8010, docling-stub), appuser, CI em contêiner.
  Relatório: [docs/blocks/B00b.md](blocks/B00b.md).
- **B01** — core: 15 modelos Pydantic, chaves de upsert, tabela de transições,
  Protocols, 15 JSON Schemas gerados com verificação no CI.
  Relatório: [docs/blocks/B01.md](blocks/B01.md).
- **B04 (parte antecipada)** — contrato de ingestão: IngestResult, texto
  canônico NFC, mapa de parágrafos com locate(offset) → "cap. X, § Y",
  pdf_loader adaptado, relatório de revisão em data/processed/<hash>/.
  Relatório: [docs/blocks/B04.md](blocks/B04.md).
- **B04-docs** — CLI (`python -m map_relations ingest`), Dockerfile
  multi-stage, Makefile, README, architecture.md, mapa do projeto
  (imports.svg, codigo_morto.txt, fluxo.md, arquivos.md), phases.md.
  Relatório: [docs/blocks/B04-docs.md](blocks/B04-docs.md).
- **B04-pkg** — map_relations instalável (hatchling): imports `map_relations.*`,
  sem PYTHONPATH; editável na dev, não editável na prod; CI com cache GHA.
  Relatório: [docs/blocks/B04-pkg.md](blocks/B04-pkg.md). ADR 007.
- **B04b-prova** — correções genéricas no canônico (letras espaçadas,
  precedência de títulos explícitos, alertas de capítulo vazio e de regra de
  maiúsculas); serviço docling real + `make compare` / `make compare-all` com
  relatório pdf_loader × Docling; eval/pdfs/ preparado para 3–5 PDFs do Leon.
  Relatório: [docs/blocks/B04b-prova.md](blocks/B04b-prova.md).
- **B04c** — Markdown intermediário único (ADR 008): conversores
  (Docling/pdf_loader/TXT/pandoc) geram documento.md revisável com
  `<!-- p.N -->`; parser único → IngestResult (subtítulo e página no
  contrato); layout data/processed/<hash_do_arquivo>/ com cache Docling por
  versão+opções; CLI ingest/prepare/compare/clean; make ingest roda o Docling
  no cache miss; clean-processed lista órfãs (APPLY=1 remove).
  Relatório: [docs/blocks/B04c.md](blocks/B04c.md).
- **B04c (ajustes 2026-11-13)** — alertas calculados sobre o documento.md
  atual, com seção "Da conversão" marcando resolvidos; Docling por faixas de
  40 páginas em processos separados (merge nos MdBlocks, página absoluta, regra
  de parágrafo na fronteira). O documento de teste inteiro (379 p.) convertido sem OOM,
  pico 2,45 GiB por faixa. Relatório: [docs/blocks/B04c.md](blocks/B04c.md).

## Em andamento

- **B04d (Opção B, fases 0-2)** — branch `b04d-cabecalho`. Camada comum de
  layout entre conversores: `ingest/layout.py` com `LayoutItem`/`BBox`/
  `LayoutLabel` (fase 0); adaptador Docling devolve `LayoutItem` via
  `DOCLING_LABEL_MAP` exaustivo sobre `DocItemLabel` — `docling-core` entrou
  como dependência de dev só para esse teste (fase 1); `join_crossing_items`,
  `classify_titles` (as 4 mensagens de alerta citadas no plano, preservadas
  literalmente) e `drop_page_furniture` saem do Docling/`canonical.py` para
  `layout.py`, um commit por regra (fase 2). `is_explicit_heading`/`_despace`
  também saíram de `canonical.py` para `layout.py`; `canonical.py` mantém os
  dois como re-export. Fases 0-4 são refatoração pura: nenhum teste existente
  foi editado. Plano completo: [docs/plans/B04d.md](plans/B04d.md).

## Pendências

- Leon: adicionar 3–5 PDFs de diagramação variada em data/raw/ e listá-los em
  eval/pdfs/conjunto.txt; depois `make compare-all`.
- Subtítulo em caixa mista grudado no título pelo Docling (ex.: "C A P Í T U L O
  IV A AMIGA DA MENINA BÜRSTNER"): corrigido na revisão humana do documento.md.
- Revisão humana dos blocos B04, B04-docs, B04-pkg, B04b-prova e B04c (docs/blocks/).
- Criar repositório remoto no GitHub (map-relations) — aguardando a conta do Leon.
- Resto do B04: leitura de TXT e EPUB; migrar url_loader ao contrato
  IngestResult (hoje é o único candidato real em codigo_morto.txt).
- B02: gabarito eval/gold/processo.json e comando eval.
- Limitação conhecida do pdf_loader: parágrafo que atravessa página sem hífen
  vira dois parágrafos; resolve-se com Docling no B04b.

## Decisões recentes (com o número do ADR)

- ADR 001 — CVEs da imagem base: 2 corrigidos (zlib1g), 47 aceitos sem fix.
- ADR 002 — Docker Desktop: `user: "0:0"` no compose local; appuser na imagem.
- ADR 003 — UUID como identidade + chaves de conteúdo para upsert.
- ADR 004 — offsets em code points sobre texto NFC.
- ADR 005 — só LlmEngine.complete é async; tarefas com gather + semáforo.
- ADR 006 — tabela de transições de estado; ChangeLog em toda mudança.
- ADR 007 — map_relations como pacote instalável (hatchling); sem PYTHONPATH.

## Handoff

**Próximo passo exato:** na branch `b04d-cabecalho`, seguir o plano
[docs/plans/B04d.md](plans/B04d.md) a partir da **fase 3 — rota pdf_loader
pela camada comum**: `canonical.pdf_pages_to_blocks` vira adaptador;
`_split_paragraph_blocks` (desifenização, colapso de espaço, isolamento de
título) fica no adaptador (é texto→itens, não pós-processamento) e passa a
produzir `LayoutItem` com `page`, sem `bbox`; a regra "quebra de página é
quebra de bloco, exceto hífen" passa a ser a mesma `layout.join_crossing_items`
da fase 2.1. Nesse ponto, `canonical._clean_pages`/`_find_repeated_edges`
também devem trocar para `layout.drop_page_furniture` (fase 2.3 deixou a
função pronta e testada, mas sem nenhum chamador ainda — `canonical.py` não
foi tocado de propósito, por depender do adaptador pdf_loader que só a fase
3 cria). Fase 4 (TXT e pandoc) vem depois, fase 5 é a regra nova (faixa do
corpo) e fase 6 é comparação + reconhecimento do MinerU. Mesmas regras de
antes: fases 0-4 não editam teste existente; `make check` e a tarefa ci
verdes ao fim de cada fase; revisar com o Leon antes de seguir para a fase 5
(regra de comportamento nova).

Nota de interpretação registrada ao Leon (fases 0-2, não é desvio do plano,
é uma ambiguidade textual resolvida): o parágrafo da fase 1 diz "furniture_hint
em vez de _EDGE_LABELS" mas também "capturar [content_layer], não usar" — a
implementação manteve a remoção de cabeçalho/rodapé pelo rótulo nativo
(equivalente a `_EDGE_LABELS` de antes) e só capturou `furniture_hint` sem
usá-lo pra decidir, priorizando "nenhum teste existente muda" sobre a leitura
literal da primeira frase. Rever se isso bate com a intenção ao chegar na
fase 5 (onde `furniture_hint`/bbox passam a decidir de verdade).

**Como retomar:** ler CLAUDE.md e este arquivo; `make check` deve passar
(lint + typecheck + schema-check + 200 testes em Docker); `make map` regenera
o mapa. A CLI de ingestão é `make ingest PDF=<arquivo em data/raw>`.
docling-core entrou como dependência de dev (pyproject.toml, uv.lock) só para
o teste de exaustividade do mapa de rótulos do Docling (fase 1) — pacote
leve (pydantic, sem torch); o serviço docling continua isolado na imagem
própria.

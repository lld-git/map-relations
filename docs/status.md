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

- **B04d (Opção B, fases 0-5)** — branch `b04d-cabecalho`. Camada comum de
  layout entre conversores: `ingest/layout.py` com `LayoutItem`/`BBox`/
  `LayoutLabel` (fase 0); adaptador Docling devolve `LayoutItem` via
  `DOCLING_LABEL_MAP` exaustivo sobre `DocItemLabel` — `docling-core` entrou
  como dependência de dev só para esse teste (fase 1); `join_crossing_items`,
  `classify_titles` (as 4 mensagens de alerta citadas no plano, preservadas
  literalmente) e `drop_page_furniture` saem do Docling/`canonical.py` para
  `layout.py`, um commit por regra (fase 2). `is_explicit_heading`/`_despace`
  também saíram de `canonical.py` para `layout.py`; `canonical.py` mantém os
  dois como re-export.
  Fase 3: `canonical.pdf_pages_to_blocks` vira adaptador — remoção de
  cabeçalho/rodapé/número de página passa a `layout.drop_page_furniture`
  (sobre a 1ª/última linha não vazia de cada página) e a junção de parágrafo
  entre páginas passa a `layout.join_crossing_items`; `classify_headings`
  (precedência de títulos do pdf_loader) fica onde estava — as mensagens de
  alerta são literalmente diferentes das do Docling, e `test_ingest_contract`
  confere o texto do pdf_loader.
  Fase 4: extraído `canonical.layout_items_to_blocks` (o pós-processamento
  comum que `pdf_pages_to_blocks` já fazia); TXT e pandoc passam a usá-lo em
  vez de chamar `classify_headings` direto, virando `LayoutItem` numa só
  faixa, sem `page` nem `bbox` — confirma que isso desliga a regra de borda
  sem caso especial.
  Fase 5 (regra nova, Opção A): `layout.compute_body_band` (percentis 5º/95º
  das bboxes dos itens de corpo do documento inteiro; não confiável com
  menos de 3 páginas com bbox) e `layout.apply_body_band` — cabeçalho/rodapé
  **dentro** da faixa volta a ser texto, na posição original (com alerta de
  reclassificação, para o report.md); **fora**, continua removido; número
  de página fora da faixa é removido mesmo rotulado `text`; dentro, é
  mantido. Faixa não confiável ou item sem bbox: fallback idêntico a antes
  da fase 5. `convert_docling.docling_items` parou de remover
  page_header/page_footer na extração — o item sobrevive como `LayoutItem`
  para a regra da faixa decidir; `merge_range_docs` calcula a faixa uma vez
  sobre o documento inteiro (depois do merge de faixas de página do B04c) e
  só então aplica a cada faixa, antes de `join_crossing_items`.
  Fases 0-4 são refatoração pura: nenhum teste existente foi editado (209
  testes verdes: 200 de antes + 9 novos — E1, F1-F7, E3). Plano completo:
  [docs/plans/B04d.md](plans/B04d.md).

## Pendências

- B04d fase 6 (último passo do plano): `make compare` sobre qualquer
  conversor registrado; reconhecimento do MinerU (B.3, sem adaptador) — ADR
  com os campos reais da saída, licença conferida e custo medido.
- B04d: regenerar data/processed com o PDF real (o_processo.pdf, já em
  data/raw/) e colar no relatório do bloco o resumo do ingest e a seção de
  itens reclassificados do report.md (critério de pronto do plano, item 3)
  — não rodou nesta sessão (conversão Docling pesada: faixas de 40 páginas,
  ~2,45 GiB de pico cada, ver B04c).
- B04d: teste E2 do plano (caso "K." ponta a ponta nas duas rotas) não foi
  escrito — ver Handoff.
- B04d: ADR curto registrando a decisão pela Opção B e o motivo (critério de
  pronto do plano, item 5); docs/architecture.md e docs/mapa ainda não
  refletem a camada comum (item 6).
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
[docs/plans/B04d.md](plans/B04d.md) a partir da **fase 6 — comparação e
MinerU**: `make compare` sobre qualquer conversor registrado (hoje só aceita
Docling × pdf_loader); reconhecimento do MinerU Basic (B.3), sem escrever
adaptador — rodar uma vez sobre o PDF de teste, registrar em `docs/adr` os
campos reais da saída (`content_list.json`/`middle_json.json`, nome do
campo, unidade e origem do bbox — a documentação oficial não especifica),
confirmar a licença no `LICENSE` do repositório e medir o custo (tamanho de
imagem, tempo por faixa).

Depois da fase 6, falta para o bloco inteiro (critério de pronto do plano):
regenerar `data/processed` com `o_processo.pdf` (já em `data/raw/`) e colar
no relatório do bloco o resumo do ingest e a seção de itens reclassificados
do `report.md` (sem ler arquivos inteiros — `head`/`grep`/offset); ADR curto
da escolha pela Opção B; `docs/architecture.md` e `docs/mapa` atualizados
com a camada comum.

**Pendência de teste, não de código:** o plano pede um teste E2 ("K." ponta
a ponta nas duas rotas: página A termina sem pontuação final, página B abre
com o falso cabeçalho dentro da faixa → "… disse K." no canônico, pelas duas
rotas). Não escrevi — a regra de junção hoje (`join_crossing_items`/
`_continues_paragraph`) só junta quando o lado seguinte começa com letra
minúscula, e "K." começa com maiúscula (nome próprio); um teste fiel ao
exemplo do plano dependeria de decidir se isso deve passar a juntar nomes
próprios também, o que é mudança de regra, não só de teste. Perguntar ao
Leon antes de escrever.

**Nota de interpretação resolvida (chegou a fase 5):** a dúvida das fases
0-2 sobre `furniture_hint` ficou resolvida pela própria leitura do plano —
`furniture_hint` é descrito como sugestão do conversor ("quem decide é a
regra da faixa"); a decisão real ficou com bbox + `_within_band`
(`layout.apply_body_band`), e `furniture_hint` continua carregado só para
diagnóstico, nunca lido por nenhuma regra. Nenhuma ação pendente aqui.

**Como retomar:** ler CLAUDE.md e este arquivo; `make check` deve passar
(lint + typecheck + schema-check + 209 testes em Docker); `make map` regenera
o mapa. A CLI de ingestão é `make ingest PDF=<arquivo em data/raw>`.
docling-core entrou como dependência de dev, fixada em `2.107.1` — igual à
versão instalada no serviço docling (`docker/docling/Dockerfile`), para o
mapa de rótulos não divergir entre os dois; confirmado nos dois lugares
antes da fase 3 desta sessão. `DocItemLabel` tem 30 valores nessa versão
(e também em 2.106.0, idêntico) — o "31" do plano (seção B.2) é uma
contagem equivocada no texto, não uma versão diferente do enum;
`DOCLING_LABEL_MAP` já tem as 30 entradas, exaustivo (testado em
`test_layout.py`).

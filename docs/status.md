# Status — atualizado em 2026-11-21 (B04f falas)

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

## Concluído (cont.)

- **B04d (Opção B, completo)** — branch `b04d-cabecalho`. Camada comum de
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
  (precedência de títulos do pdf_loader) fica onde estava.
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
  mantido.
  Fase 6: `docling_compare.compare` passou a operar sobre `LayoutItem[]` em
  vez do JSON nativo do Docling — `CONVERTERS` em `__main__.py` registra
  `docling` e `pdf_loader`, e `make compare --converter <nome>` escolhe qual
  comparar contra o pdf_loader; reconhecimento do MinerU Basic rodado uma
  vez (ADR 010), sem adaptador.
  **Decisão do E2** (fechada nesta sessão, Leon): bloco sem pontuação final
  une ao seguinte mesmo que comece com maiúscula (nome próprio, ex. "K." no
  início de página), exceto se o seguinte começa com travessão de fala, é
  título ou item de lista, ou se o anterior é título — implementado em
  `layout._continues_paragraph`/`join_crossing_items`; testes E2 nas duas
  rotas (unidade em `test_layout.py`; ponta a ponta em
  `test_docling_ranges.py` e `test_ingest_contract.py`).
  `classify_titles` (Docling) e `canonical.classify_headings` (pdf_loader)
  **não foram unificadas** — ver Pendências.
  213 testes verdes (209 de antes + 4 do E2). ADR 009 (Opção B) e ADR 010
  (MinerU). `data/processed` apagado e regerado do zero com `o_processo.pdf`:
  129 páginas, 1399 parágrafos, 10 capítulos, 0 itens removidos, 0 alertas
  ativos; 0 itens reclassificados pela faixa do corpo (este PDF não tem
  cabeçalho/rodapé/numeração repetida no corpo — já sabido do B04b-prova, a
  faixa simplesmente não teve o que corrigir). `make check` e os dois jobs
  do CI (test + build-prod) verdes localmente. Plano completo e relatório:
  [docs/plans/B04d.md](plans/B04d.md), [docs/blocks/B04d.md](blocks/B04d.md).
  **Mesclado no master** via PR #2 (2026-11-20, commit `5b3fb28`).
- **B04e** — branch `b04e-subtitulo`, a partir do master com o B04d já
  mesclado. Correção genérica no E2: o primeiro bloco depois de um título
  explícito de capítulo (o subtítulo, ex. "Conversa com a senhora
  Grubach...") nunca é unido ao seguinte por `join_crossing_items` — evita
  fundir um subtítulo sem ponto final com a primeira frase da página
  seguinte. Exceção preservada: palavra hifenizada na fronteira continua
  unida mesmo logo depois de um título (é a mesma palavra partida, nunca
  um subtítulo) — sem isso um teste real de hifenização quebrava.
  `layout.detect_chapter_subtitle_alerts` gera o alerta "possível
  subtítulo de capítulo" para esse bloco quando tem até 15 palavras e não
  termina em pontuação final, ligado nas duas rotas (Docling via
  `items_to_blocks`; pdf_loader/TXT/pandoc via `layout_items_to_blocks`).
  4 testes novos (217 no total). `make check` e os dois jobs do CI (test +
  build-prod) verdes localmente. Relatório: [docs/blocks/B04e.md](blocks/B04e.md).

- **B04f** — branch `b04f-falas`, a partir do master com o B04e já mesclado.
  Travessão/hífen de fala não se perdia mais na extração, mas sobrevivia só
  até o `documento.md`: editores Markdown liam a linha como item de lista.
  Duas correções: (1) `convert_docling.items_to_blocks` agora usa
  `marker + " " + text` para item `list_item` do Docling (o marcador já
  chegava em `LayoutItem.marker`, mas não era usado ao montar o bloco);
  (2) `markdown.render_markdown`/`parse_blocks` escapam com `\` só o início
  de linha de parágrafo que começa com `-`, `–`, `—` ou `―` — o canônico não
  muda, só o `.md` deixa de ser lido como lista; hífen no meio da linha
  continua sem escape. 3 testes novos (220 no total):
  `test_list_item_keeps_docling_marker_as_dash_prefix` em
  `test_docling_ranges.py`; `test_leading_dash_escaped_in_md_but_not_in_canonical`
  e `test_dash_in_middle_of_line_is_not_escaped` em `test_markdown.py`.
  `make check` (lint/typecheck/schema-check/test, escopados a
  research/tests/scripts — ver nota abaixo) e os dois jobs do CI (test +
  build-prod, reproduzidos localmente a partir de uma cópia limpa do índice
  do git, sem os arquivos não versionados) verdes. Sem push desta sessão.

**Nota sobre `make check` nesta sessão:** `ruff check .` (alvo `lint` do
Makefile) falha por 10 erros em `golden_scripts/` — diretório não
versionado, de um trabalho anterior não relacionado a este bloco (confirmado
com `git stash`: o erro já existia antes de qualquer mudança do B04f). Não é
baked só por estar no disco: a imagem Docker local tem `golden_scripts/`
copiado em camada (`COPY --chown=appuser:appuser . .` no Dockerfile), então
mesmo movendo a pasta do host o container antigo ainda a via — só desaparece
reconstruindo a imagem a partir de um contexto sem ela. Por isso os dois jobs
do CI foram reproduzidos localmente com `git checkout-index` (cópia só do
que está no índice do git, igual ao `actions/checkout` real) em vez de
`docker compose`, que usa o diretório de trabalho inteiro. `ruff check .`
passa nessa cópia limpa — a falha é só do disco local. Resolver
`golden_scripts/` (versionar, mover para fora do contexto Docker ou
corrigir o lint) é decisão do Leon, fora do escopo deste bloco.

## Pendências

- **B04d: `classify_titles`/`classify_headings` não unificados.** Tentei
  nesta sessão (passar a variante da mensagem como parâmetro, preservando
  as mensagens literalmente) e não é viável só com isso: os dois sinais
  fracos de título são de natureza diferente — `classify_titles` lê
  `LayoutItem.label is LayoutLabel.titulo` (sinal estrutural do conversor)
  e promove um título fraco adjacente a um forte para `subtitulo`;
  `classify_headings` lê uma heurística de texto (linha toda em maiúsculas)
  e não tem o conceito de subtítulo. Unificar de verdade exigiria também
  decidir se o pdf_loader passa a ter subtítulo (mudança de comportamento,
  não só de código) e marcar `LayoutLabel.titulo` nas linhas em maiúsculas
  do pdf_loader antes do `join_crossing_items` (hoje elas chegam como
  `texto`). Fica para outro bloco, com decisão do Leon sobre o subtítulo.
- **B04d: licença do MinerU não confirmada no `LICENSE` do repositório**
  porque **o repositório não tem esse arquivo** — não há remoto no GitHub
  ainda (ver pendência abaixo). A licença real (lida do pacote, ADR 010) é
  Apache 2.0 + termos adicionais do MinerU Team (uso comercial livre até
  100M MAU/USD 20M de receita mensal; atribuição obrigatória se expuser
  parsing via MinerU a terceiros). Decisão de criar o `LICENSE` e escolher
  os termos do projeto é do Leon.
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
- ADR 008 — Markdown estruturado como formato intermediário único.
- ADR 009 — B04d: camada comum de layout entre conversores (Opção B).
- ADR 010 — Reconhecimento do MinerU Basic: campos reais, licença, custo.

## Handoff

**B04f está fechado** (branch `b04f-falas`, a partir do master com o B04e já
mesclado; sem push desta sessão). Marcador de lista do Docling preservado no
bloco e escape de travessão/hífen de fala só no início da linha do
`documento.md` — ver bullet B04f acima. Sem relatório dedicado em
`docs/blocks/` (bloco pequeno, pontual); detalhe completo no bullet do
Status.

**B04e está fechado** (branch `b04e-subtitulo`, a partir do master com o
B04d já mesclado via PR #2; sem push desta sessão). Correção pontual do
E2 — ver bullet acima e [docs/blocks/B04e.md](blocks/B04e.md).

**B04d está fechado e mesclado no master** (PR #2, commit `5b3fb28`).
Critério de pronto do plano revisado item a item:

1. `make check` e os dois jobs do CI (test + build-prod) verdes localmente
   — ok.
2. Testes do plano — ok, exceto a unificação opcional de títulos (não fazia
   parte da lista de testes do plano em si).
3. `data/processed` apagado e regerado com `o_processo.pdf` — ok: 129
   páginas, 1399 parágrafos, 10 capítulos, 0 removidos, 0 alertas ativos; 0
   itens reclassificados pela faixa do corpo (ver nota abaixo).
4. Nenhuma regra cita nome/título/padrão do livro de teste — ok (inalterado
   desde o B04b-prova).
5. ADR da decisão (Opção B) — ok, [ADR 009](adr/009-camada-comum-layout.md).
6. `docs/architecture.md` e `docs/mapa` atualizados — ok.
7. Fases 0-4 sem edição de teste existente — ok (209 testes antigos
   intocados; só os novos E1-E3/F1-F7/E2 foram acrescentados).
8. ADR do MinerU com campos reais, licença e custo — ok,
   [ADR 010](adr/010-reconhecimento-mineru.md), com a pendência da licença
   registrada acima (falta o arquivo `LICENSE` em si, decisão do Leon).

**Nota sobre o item 3 (itens reclassificados):** `report.md` não tem uma
seção dedicada a reclassificação — os alertas de `apply_body_band`
("… dentro da faixa do corpo volta a ser texto …") apareceriam misturados
em "Alertas"/"Da conversão" se existissem. Para `o_processo.pdf` não
existe nenhum: o PDF não tem cabeçalho/rodapé/numeração repetida no corpo
(já achado no B04b-prova), então a regra da faixa não teve nada para
corrigir nesta obra — comportamento correto, não um bug da regra. As 5
alertas de "Da conversão" são todas sobre títulos em maiúsculas/letras
espaçadas não numerados como capítulo (ex.: "ÍNDICE", "F Fr ra an nz z
K Ka af fk ka a"), sem relação com a faixa do corpo.

**Nota de interpretação resolvida (da fase 5):** a dúvida das fases 0-2
sobre `furniture_hint` ficou resolvida pela própria leitura do plano —
`furniture_hint` é descrito como sugestão do conversor ("quem decide é a
regra da faixa"); a decisão real ficou com bbox + `_within_band`
(`layout.apply_body_band`), e `furniture_hint` continua carregado só para
diagnóstico, nunca lido por nenhuma regra.

**Próximo bloco (fora do B04d/B04e):** resto do B04 (TXT/EPUB), migração do
`url_loader`, B02 (gabarito e comando eval), ou abrir um bloco para a
unificação de títulos pdf_loader/Docling — decisão do Leon sobre qual vem
primeiro.

**Como retomar:** ler CLAUDE.md e este arquivo; `make check` deve passar
(lint + typecheck + schema-check + 217 testes em Docker); `make map`
regenera o mapa. A CLI de ingestão é `make ingest PDF=<arquivo em
data/raw>`; `make compare PDF=<arquivo> [--converter docling|pdf_loader]`
(via `python -m map_relations compare ... --converter`). docling-core é
dependência de dev, fixada em `2.107.1` — igual à versão instalada no
serviço docling (`docker/docling/Dockerfile`). O serviço MinerU
(`docker/mineru/Dockerfile`, perfil `mineru`) precisa de
`mineru-kit models download --tier basic` antes do primeiro `mineru-kit
parse`; os modelos ficam no volume nomeado `mineru_models`, não em
`data/`.

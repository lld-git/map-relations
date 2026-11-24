# Status — atualizado em 2026-11-24 (B02, fases 0 a 3 + revisão do formato; próxima: sessão 3b)

Ordem dos blocos: B04 foi antecipado antes do B02 (decisão do Leon em
2026-11-11), porque os offsets do gabarito referenciam o texto canônico.
Ordem atual: B00 → B00b → B01 → **B04** → B02 → B02b → B03 → B04 (TXT/EPUB) → B04b → B05…

## Concluído

- **B02a** — ontologia de relações, branch `b02a-ontologia` (sem push).
  YAML versionado com trava de ids, `Ontology`, artefatos gerados, `claim_key`
  lendo a simetria do `RelationType` (com `asserted_by` e `narrative_scope` na
  chave, classe fora), `rules.new_claim` (rejeita abstrato, obsoleto e
  reflexivo; disjunção é alerta), classe `alegada`, `narrative_scope`.
  `vigia` renomeado para `exerce_vigilancia_sobre` antes de publicar a trava.
  270 testes. ADR 011. Relatório: [docs/blocks/B02a.md](blocks/B02a.md).
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

- **Infra (mesma sessão, após o B04f)** — resolvida a nota acima sobre
  `golden_scripts/`: `pyproject.toml` agora exclui `golden_scripts/` do
  ruff (`[tool.ruff] extend-exclude`) e do mypy (`[tool.mypy] exclude`,
  junto com `docs/mapa/vulture_whitelist.py` — achado ao tirar a restrição
  manual de escopo: esse arquivo não é código executável do projeto,
  mesma categoria do `golden_scripts/`, e `mypy .` sem exclusão o
  rejeitava com "Cannot access instance-only attribute"). `make typecheck`
  e o job `test` do CI passaram a rodar `mypy .` (sem a lista manual
  `research tests scripts`); `make lint` já rodava `ruff check .`.
  `.dockerignore` já excluía `golden_scripts/` e `data/golden/` (preso no
  working tree, nunca comitado — comitado agora junto). A imagem Docker
  local (`maprelations-app`) estava com `golden_scripts/` preso de uma
  camada `COPY` anterior ao `.dockerignore` atual; reconstruída do zero,
  confirmado que não aparece mais. `make check` roda o projeto inteiro
  sem restrição manual de escopo, verde (220 testes).
  Imagens Docker padronizadas: `painel` não tem mais `build:` próprio —
  usa `image: maprelations-app`, a mesma do serviço `app` (nomeada
  explicitamente no compose, igual ao nome que o Compose já gerava, agora
  fixo); a tarefa `build-prod` do CI já usava `map-relations-prod` (sem
  mudança). Registrado em CLAUDE.md (princípio 14): nome de imagem só vem
  do Makefile/docker-compose.yml, nunca `docker build`/`tag` manual fora
  disso, e `docker image prune` depois de todo rebuild — a VM do Docker
  Desktop aqui tem pouco espaço (ficou em ~2 GiB livres durante esta
  sessão; `docker image prune -f` e `docker builder prune -f` liberaram
  o suficiente para a imagem `dev` reconstruir).

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
- B02: gabarito em `data/golden/processo.json` (fora do Git) e comando eval.
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
- ADR 011 — Ontologia de relações versionada; `claim_key` pelo RelationType; `alegada`.

## Handoff

**B02a concluído** (branch `b02a-ontologia`, sem push; relatório em
[docs/blocks/B02a.md](blocks/B02a.md)). Além da parte da ontologia (YAML, `Ontology`,
trava, geração), o bloco agora tem `claim_key(s, RelationType, o, *, asserted_by,
narrative_scope)`, `rules.new_claim`, `ClaimClass.alegada`, `Claim.asserted_by` e
`Claim.narrative_scope`, `make schema`, CLAUDE.md (modelo e seção B02) e ADR 011.
`vigia` virou `exerce_vigilancia_sobre` (trava regenerada do zero, ainda não
publicada). 270 testes; `make check` e os dois jobs do CI verdes.

**Plano do B02 aprovado** em [docs/plans/B02.md](plans/B02.md) (2026-11-21),
com D1–D9 fechadas. Destaques: 38 dos 40 offsets do rascunho estão velhos
(hash do canônico mudou), e o fill-offsets vem antes de tudo. A avaliação tem
duas medidas, estrita (com `asserted_by`) e relaxada (sem `asserted_by` nem
classe). O capítulo de controle é o cap. 5, que exige uma anotação do modelo
para esse capítulo, ainda sem responsável definido.

**B02 em andamento** na branch `b02-gabarito` (a partir do master `2fbe888`, sem
push; o plano previa `b02-avaliacao`, o nome foi trocado por decisão do Leon).
Feitas as fases 0 a 3 do plano (§2 a §6); as fases 2 e 3 num só commit:
- **Fase 0 — `make ci`:** `ci-test` e `ci-prod` espelham os dois jobs do
  `ci.yml` (sem volumes, `appuser`); `tests/test_ci_sync.py` falha se os `docker
  run` ou o `target` divergirem. Desvio do plano: o contexto do build é
  `git archive $(git write-tree)` (o índice de verdade), não `git ls-files | tar`,
  que empacotava a árvore de trabalho e deixou vazar uma modificação não staged.
  Consequência: `git add` antes de `make ci`. `.github/` saiu do `.dockerignore` e
  Makefile/.github entram como volumes `:ro` para o teste rodar no `make check`.
- **Fase 1 — gabarito:** `evaluation/gold.py` (`GoldFile`, `Anchor` com exact,
  prefix, suffix, startOffset e endOffset, `check_anchor`, `validate_gold`,
  `relation_id`), `contracts/schemas/gold.schema.json` gerado e conferido no
  `generate_schemas --check` (CI), ADR 012, 51 testes novos (um por regra do §3).

- **Fase 2 — fill-offsets (§5):** `evaluation/anchoring.py` (`resolve_anchor`:
  1 ocorrência aceita; várias filtram só por `prefix`/`suffix` gravados; offset
  antigo, ordinal e casamento aproximado nunca decidem; contexto de 32 que cresce
  até 128 sem cortar palavra), `evaluation/fill_offsets.py` (tudo ou nada, modo âncora
  mínima, relatório sem texto da obra), subcomandos `gold fill-offsets` e
  `gold validate` (pendência da fase 1 resolvida), `make gold-fill`/`gold-validate`.
- **Fase 3 — conversão (§6):** `evaluation/convert_draft.py`, `gold convert-draft`,
  `make gold-convert`. O relatório da citação ambígua mostra só `cap. X, § Y` e até
  5 palavras de cada lado, nunca a citação. Desvio do plano: o rascunho aceita as
  chaves opcionais `prefix`/`suffix` por relação, que é o canal da decisão D4.
  42 testes novos (370 no total).
  **Rodada real sobre o canônico atual (hash `7a25…`): 38 relações convertidas, 1 com
  erro (ambígua, a relação #3 do rascunho, 2 ocorrências no cap. 1, § 24 e § 51).
  `processo.gold.json` NÃO foi gerado (tudo ou nada).** O rascunho tem 39 relações
  (o plano dizia 40). Relatório JSON em `data/golden/processo.convert-report.json`.

**Revisão do formato (2026-11-24, mesma branch, 1 commit depois das fases 2 e 3):**
- **Evidências** (ADR 012): `evidence` é lista de 1+ itens `{chapter, anchor, support
  (alto|medio|baixo), polarity (apoia|contradiz), note?}`; `anchor.exact` obrigatório,
  o resto da âncora vem do fill-offsets (que agora refaz só `evidence[j].anchor`).
  Provada = evidência alta que apoia **ou** `provas_em_conjunto: suficiente`. O peso
  (alto=3, medio=2, baixo=1; só das que apoiam) não decide: só gera alerta se o conjunto
  foi declarado suficiente e a soma fica abaixo do corte (4). **Pesos e corte são
  provisórios, a calibrar no B03.** Nada calculado é gravado (sem `quote`,
  `support_profile`, `support_weight`, `prova_status`, `also_in_chapters`; `extra=forbid`
  os rejeita); os valores saem em `GoldReport.proofs` e no `gold validate`.
  `chapter` é conferido contra `locate()`. A conversão cria 1 evidência alta que apoia
  por relação. Esses campos calculados nunca existiram no código; o que mudou foi o
  formato de `evidence`.
- **Nomes → ids:** já era assim na conversão (casamento exato por `preferredName`/alias,
  desconhecido ou ambíguo = erro listado, id = slug do `preferredName`, colisão = erro);
  ganhou testes (mesmo id em qualquer capítulo/execução, sem casamento aproximado).
- **Ontologia:** `when_to_use` de `vinculo_amoroso_com` ganhou "interesse manifestado
  pelos dois lados na mesma cena". A trava exigiu subir `version` desse tipo (1 → 2)
  porque o conteúdo mudou; nenhum id mudou e o hash `semantic` ficou igual. Regenerado
  com `make schema` (generate_ontology).
- **Imagem prod:** confirmado que continha `.github/` e `Makefile` (o `COPY . .` do
  B02 fase 0). Agora o Dockerfile tem o estágio descartável `ctx` que os remove e o
  `prod` copia dele (nenhuma camada do prod os tem); o `dev` os recebe por `COPY`
  próprio (o `test_ci_sync` precisa). Passo novo no `ci.yml` e no `make ci-prod`:
  `test ! -e .github && test ! -e Makefile` na imagem prod.

**Decisão sobre o fluxo do bloco:** depois deste commit, o B02 é mesclado no master e
o §9 (capítulo de controle: `gold template`, `gold compare`, anotação do modelo e do
Leon para o cap. 5) vira um **bloco separado**. Ficam no B02: fases 4 (§7), 5 (§8) e 7.
A fase 6 sai.

**Próximo passo exato: sessão 3b — §7 (avaliação) e §8 (MLflow).** Fase 4: `RunFile`,
alinhamento, casamento (estrito e relaxado), métricas e `eval`; fase 5: `RunTracker`,
`MlflowTracker`, serviço `mlflow`, ADR 013. Atenção ao novo formato: só relações
**provadas** (`GoldReport.proofs`) devem entrar como gabarito positivo do `eval`, e
evidências `contradiz` não contam como prova. Antes: o Leon ajusta o rascunho, resolve a
relação #3 (D4, `prefix`) e roda `make gold-convert` para gerar `processo.gold.json`
(ainda não existe); conferir (a) `narrative_scope = obra`, (b) a regra do
cabeçalho/rodapé em `annotation_rules`, (c) `make gold-validate GOLD=…`. A sessão 3b
não precisa do gabarito real: usa fixtures sintéticas.

**Pontos abertos:** (a) a trava protege só a parte semântica dos abstratos (não têm
`version`); a visão inversa herda o `version` do dono. (b) Erros estruturais do YAML
param antes das regras semânticas; os demais saem juntos. (c) `age_em_nome_de` ×
`representa_juridicamente` segue para a avaliação por família no B02. (d) `uv lock`
exige montar o diretório (`docker run -v "$PWD":/work -w /work maprelations-app uv
lock`). (e) Regra do verificador para `alegada`: B05.

**Como retomar:** ler CLAUDE.md, este arquivo e docs/plans/B02.md (§7, §8 e §11); `make check` verde.
`docs/arquitetura_sugest.md` continua não versionado (não é deste bloco).

---

### Handoff anterior (B04f/B04e/B04d)

**B04f está fechado** (branch `b04f-falas`, a partir do master com o B04e já
mesclado; sem push desta sessão). Marcador de lista do Docling preservado no
bloco e escape de travessão/hífen de fala só no início da linha do
`documento.md` — ver bullet B04f acima. Sem relatório dedicado em
`docs/blocks/` (bloco pequeno, pontual); detalhe completo no bullet do
Status.

**Infra de lint/typecheck/Docker corrigida na mesma sessão, mesma branch**
(commit separado, depois do B04f): `golden_scripts/` excluído de
ruff/mypy via `pyproject.toml`; `make check` roda sem escopo manual;
`painel` reusa a imagem `maprelations-app` em vez de buildar a própria;
princípio novo no CLAUDE.md sobre nome de imagem e `docker image prune`
— ver bullet "Infra" acima.

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

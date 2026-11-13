# Status — atualizado em 2026-11-13

Ordem dos blocos: B04 foi antecipado antes do B02 (decisão do Leon em
2026-11-11), porque os offsets do gabarito referenciam o texto canônico.
Ordem atual: B00 → B00b → B01 → **B04** → B02 → B02b → B03 → B04 (TXT/EPUB) → B04b → B05…

## Concluído

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
  de parágrafo na fronteira). O Processo inteiro (379 p.) convertido sem OOM,
  pico 2,45 GiB por faixa. Relatório: [docs/blocks/B04c.md](blocks/B04c.md).

## Em andamento

- Nada — bloco B04c aguarda revisão do Leon antes do B02.

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

**Próximo passo exato:** aguardar a revisão do Leon em docs/blocks/ (B04,
B04-docs, B04-pkg, B04b-prova e B04c). Aprovado, iniciar o **B02**: criar
`eval/gold/processo.json` (exemplos marcados como fictícios, offsets sobre o
texto canônico do IngestResult) e o comando
`eval --run <arquivo> --gold <arquivo>` com precisão, recall e F1 por tipo,
classe, nível e lente — critérios no bloco B02 do CLAUDE.md.

**Como retomar:** ler CLAUDE.md e este arquivo; `make check` deve passar
(lint + typecheck + schema-check + 139 testes em Docker); `make map` regenera
o mapa. A CLI de ingestão é `make ingest PDF=<arquivo em data/raw>`.

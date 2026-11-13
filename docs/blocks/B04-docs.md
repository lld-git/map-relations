# B04-docs — Documentação, CLI, Makefile e mapa do projeto
Commit: 3a4bd4c
Data: 2026-11-11

## Relatório de conclusão (verbatim)

**B04-docs concluído** — `make check` (139 testes, ruff, mypy, schema-check) e `make map` verdes, tudo em Docker. Nenhum código de domínio foi alterado. Parado para sua revisão.

**1. CLI** — `python -m map_relations ingest <pdf>` (research/map_relations/__main__.py, argparse, sem dependência nova). Valida que o PDF está em `data/raw/`, gera `data/processed/<hash>/`, imprime hash, caminho e resumo do QualityReport; sai com 2 (entrada inválida) ou 1 (falha de processamento). A imagem define `PYTHONPATH=/app/research` para o `-m map_relations` funcionar.

**2. Dockerfile multi-stage** — `base` → `prod` (execução + modelo spaCy, `uv sync --frozen --no-dev`, appuser) → `dev` (prod + grupo dev com pytest/ruff/mypy/pydeps/vulture + graphviz). Compose usa `target: dev`; o Docling continua em serviço próprio. CI refeito: job `test` roda lint, mypy, schema-check e pytest na imagem dev; job `build-prod` só constrói a prod e faz um import de sanidade.

**3. Makefile** — só chama docker compose: `test`, `lint`, `typecheck`, `schema-check`, `check`, `ingest PDF=<arquivo>` (converte para /app/data/raw/), `map`, `shell`.

**4. README.md** — requisitos (Docker, Compose ≥ 2.24, Make), configuração do .env, onde colocar PDFs, tabela de todos os alvos do Makefile com exemplo de ingestão.

**5. docs/architecture.md** — camadas, contratos (modelo de domínio, IngestResult, Protocols), links para os 6 ADRs, diagrama Mermaid de componentes em nível de módulo com o planejado tracejado, e link para docs/mapa/fluxo.md como único diagrama de fluxo.

**6. make map + mapa escrito à mão:**
- `docs/mapa/imports.svg` — pydeps com 14 módulos. **Desvio da spec:** `--cluster` colapsa tudo num único nó "research" (os módulos vivem sob `research.map_relations`), então usei módulos individuais com `--rmprefix research.map_relations.`; o motivo está comentado no Makefile.
- `docs/mapa/codigo_morto.txt` — vulture ≥ 60% com whitelist por categoria (campos Pydantic, métodos de Protocol, membros de enum): 8 candidatos, 7 são contratos usados só em testes aguardando B02–B07; a única dívida real é `url_loader` (migração pendente ao IngestResult).
- `docs/mapa/fluxo.md` — Mermaid do fluxo PDF → pdf_loader → canonical → IngestResult → data/processed/<hash>/, cada seta citando arquivo.py:função; planejado tracejado (TXT/EPUB, Docling, B02, B05); nenhuma ligação marcada com "?" — todas confirmadas no código.
- `docs/mapa/arquivos.md` — tabela de todos os .py com papel, quem importa e status.

**7. docs/status.md** — reescrito com Concluído, Em andamento, Pendências, Decisões recentes (número do ADR) e Handoff (próximo passo exato: revisão de B04/B04-docs, depois B02; como retomar: make check + make map).

**8. docs/phases.md** — B00 a B04-docs com objetivo, métricas reais (11 → 116 → 137 → 139 testes, 49 CVEs, 15 schemas, 50 pares de transição, 8 candidatos do vulture), observações e aprendizados; checkpoints C1/C1b/C2 marcados como não iniciados.

**9. CLAUDE.md** — Rotina de sessão agora diz quando atualizar cada arquivo (README, architecture, adr, blocks, status, phases, make map + fluxo + arquivos).

**Pontos para sua revisão:**
1. O desvio do `--cluster` no pydeps (item 6).
2. O CI perdeu o job rápido sem Docker (test e test-spacy no runner); agora tudo roda na imagem dev, como pedido — confirme que a troca vale a simplificação.
3. `pydeps` e `vulture` entraram no grupo dev do pyproject.toml (uv.lock atualizado dentro do contêiner).

## Revisão humana

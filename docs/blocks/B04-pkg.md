# B04-pkg — map_relations como pacote instalável
Commit: 92ff2c9
Data: 2026-11-11

## Relatório de conclusão (verbatim)

**B04-pkg concluído** — commit `92ff2c9`. `make check` (139 testes, ruff, mypy, schema-check) e `make map` verdes; `python -m map_relations ingest` confirmado nas imagens dev e prod, sem `uv run` e sem PYTHONPATH. Parado para sua revisão.

**O que mudou:**

1. **pyproject.toml** — build-system hatchling; o wheel empacota `research/map_relations` como `map_relations` (a pasta `research/` fica). Foi preciso `allow-direct-references = true` no hatch porque o modelo spaCy é dependência por URL. `known-first-party = ["map_relations", "scripts"]` no isort do ruff, senão os imports do próprio projeto seriam ordenados como third-party.
2. **uv sync instala o projeto** — editável na dev (código vivo nos volumes), não editável na prod (`uv sync --frozen --no-dev --no-editable`, código em site-packages). A prod faz duas passadas: dependências antes de copiar o código (cache de camada) e o pacote depois.
3. **PYTHONPATH removido** do Dockerfile; o Compose nunca o definiu. Acrescentei a venv ao PATH da imagem base — sem isso, `python -m map_relations` só funcionava via `uv run` (o python do sistema não via a venv), inclusive no job build-prod do CI.
4. **Imports `map_relations.*`** em todo o código (23 arquivos); `research/__init__.py` removido para não existir o caminho duplo `research.map_relations`.
5. **make map** — `pydeps --only map_relations` funciona; `--cluster` volta e produz o mesmo grafo que sem (há um único pacote de topo, nada externo para agrupar) — resultado registrado no comentário do Makefile, como pedido. 41 nós no imports.svg.
6. **Docs** — ADR 007 (decisão completa), architecture.md (nota sobre o pacote + linha na tabela de ADRs), status.md (Concluído, Decisões, Handoff). README não mencionava PYTHONPATH, ficou como estava.

**CI** — docker/build-push-action com `cache-from/to: type=gha` nos dois jobs, como você sugeriu. O build-prod agora valida o import e roda `python -m map_relations ingest --help` na imagem prod.

**Correções que a mudança revelou:**
- A CLI usava `Path(__file__).parents[2]` para achar `data/` — quebraria na prod (o arquivo fica em site-packages). Agora resolve pelo diretório de trabalho (`/app` no contêiner); registrado no ADR 007.
- O Compose passou a montar `pyproject.toml` e `uv.lock` no serviço app: sem isso, mudanças de configuração (ruff, mypy, pytest) exigiam rebuild para valer dentro do contêiner.

**Ponto para sua revisão:** o lockfile agora registra o projeto como `source = { editable = "." }`; `uv lock` continua sendo rodado dentro do contêiner com o diretório montado (`uv lock --project /work`), padrão documentado no ADR 007.

## Revisão humana

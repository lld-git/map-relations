# ADR 007 — map_relations como pacote instalável

**Data:** 2026-11-11  
**Status:** aceito

## Contexto

O pacote vivia em `research/map_relations/` e os imports eram
`research.map_relations.*`, dependentes do diretório de trabalho. Para a CLI
(`python -m map_relations`) funcionar, a imagem definia `PYTHONPATH=/app/research`
— um atalho frágil: quebra fora do contêiner, cria dois nomes para os mesmos
módulos e confunde ferramentas (o pydeps via tudo sob `research`).

## Decisão

1. **Build-system hatchling** no pyproject.toml, com
   `tool.hatch.build.targets.wheel.packages = ["research/map_relations"]`:
   a pasta `research/` permanece, mas o pacote instala como `map_relations`.
2. **`allow-direct-references = true`** no hatch, porque o modelo spaCy é
   dependência por URL (B00b).
3. **uv sync instala o projeto**: editável na imagem dev (código vivo nos
   volumes) e não editável na prod (`uv sync --frozen --no-dev --no-editable`,
   código em site-packages). A prod faz duas passadas: dependências antes de
   copiar o código (cache de camada) e o pacote depois.
4. **Imports `map_relations.*`** em todo o código; `PYTHONPATH` removido do
   Dockerfile; `research/__init__.py` removido para não existir um segundo
   caminho de import (`research.map_relations`).
5. A CLI resolve `data/` a partir do diretório de trabalho, não do pacote —
   em prod o código está em site-packages.

## Consequências

- `python -m map_relations` funciona em dev e prod sem variável de ambiente.
- `pydeps --only map_relations` volta a funcionar; `--cluster` produz o mesmo
  grafo que sem (um único pacote de topo).
- O lockfile registra o projeto como `source = { editable = "." }`; qualquer
  mudança de dependência continua exigindo `uv lock` dentro do contêiner.
- O porte para TypeScript não é afetado: contratos continuam em `contracts/`.

# Todos os alvos rodam em Docker (princípio 13 do CLAUDE.md).
# Na máquina ficam só Git, editor, Docker e navegador.

COMPOSE = docker compose
RUN = $(COMPOSE) run --rm app

.PHONY: test lint typecheck schema-check check ingest map shell

test:
	$(RUN) uv run pytest

lint:
	$(RUN) uv run ruff check .

typecheck:
	$(RUN) uv run mypy research tests scripts

schema-check:
	$(RUN) uv run python -m scripts.generate_schemas --check

check: lint typecheck schema-check test

# Uso: make ingest PDF=livro.pdf  (o arquivo deve estar em data/raw/)
ingest:
ifndef PDF
	$(error uso: make ingest PDF=<arquivo em data/raw>)
endif
	$(RUN) uv run python -m map_relations ingest /app/data/raw/$(notdir $(PDF))

# Gera docs/mapa/imports.svg (pydeps) e docs/mapa/codigo_morto.txt (vulture).
# Nota: --cluster colapsa tudo no pacote "research" (1 nó só), então fica de fora;
# --rmprefix limpa os rótulos. tests/ e __pycache__ não entram (fora do pacote).
map:
	$(RUN) uv run pydeps research/map_relations \
		--only research.map_relations \
		--rmprefix research.map_relations. \
		--noshow -T svg -o docs/mapa/imports.svg
	$(RUN) sh -c 'uv run vulture research/map_relations scripts \
		docs/mapa/vulture_whitelist.py --min-confidence 60 \
		--ignore-names "model_config,cls,req,ref,item_id,_offsets_valid,_confidence_range,_level_range" \
		> docs/mapa/codigo_morto.txt; \
		[ -s docs/mapa/codigo_morto.txt ] || echo "(nenhum candidato a código morto)" \
		> docs/mapa/codigo_morto.txt; true'

shell:
	$(RUN) bash

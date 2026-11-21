# Todos os alvos rodam em Docker (princípio 13 do CLAUDE.md).
# Na máquina ficam só Git, editor, Docker e navegador.

COMPOSE = docker compose
RUN = $(COMPOSE) run --rm app
name = $(notdir $(PDF))
stem = $(basename $(notdir $(PDF)))

# Em sincronia com DOCLING_OPTIONS_SLUG em map_relations/ingest/store.py:
# mudar as flags exige mudar o slug (e vice-versa) — cria um cache novo.
DOCLING_FLAGS = --no-ocr --no-tables --image-export-mode placeholder --page-batch-size 1

.PHONY: test lint typecheck schema-check check ingest map shell docling compare compare-all clean-processed

test:
	$(RUN) uv run pytest

lint:
	$(RUN) uv run ruff check .

typecheck:
	$(RUN) uv run mypy .

schema-check:
	$(RUN) uv run python -m scripts.generate_schemas --check
	$(RUN) uv run python -m map_relations ontology check
	$(RUN) uv run python -m scripts.generate_ontology --check

check: lint typecheck schema-check test

# Uso: make ingest PDF=livro.pdf  (o arquivo deve estar em data/raw/).
# Para PDF a rota padrão é o Docling; sem cache (exit 3), roda o serviço e repete.
ingest:
ifndef PDF
	$(error uso: make ingest PDF=<arquivo em data/raw>)
endif
	@$(RUN) python -m map_relations ingest /app/data/raw/$(name); st=$$?; \
	if [ $$st -eq 3 ]; then \
		$(MAKE) --no-print-directory docling PDF=$(name) && \
		$(RUN) python -m map_relations ingest /app/data/raw/$(name); \
	else exit $$st; fi

# Gera docs/mapa/imports.svg (pydeps) e docs/mapa/codigo_morto.txt (vulture).
# Nota: com o pacote instalável (ADR 007) os módulos chamam map_relations.* e
# --only map_relations volta a funcionar; --cluster produz o mesmo grafo que sem
# (há um único pacote de topo, nada externo para agrupar) e fica mantido por spec.
# tests/ e __pycache__ não entram (fora do pacote).
map:
	$(RUN) uv run pydeps research/map_relations \
		--only map_relations \
		--cluster \
		--rmprefix map_relations. \
		--noshow -T svg -o docs/mapa/imports.svg
	$(RUN) sh -c 'uv run vulture research/map_relations scripts \
		docs/mapa/vulture_whitelist.py --min-confidence 60 \
		--ignore-names "model_config,cls,req,ref,item_id,_offsets_valid,_confidence_range,_level_range" \
		> docs/mapa/codigo_morto.txt; \
		[ -s docs/mapa/codigo_morto.txt ] || echo "(nenhum candidato a código morto)" \
		> docs/mapa/codigo_morto.txt; true'

shell:
	$(RUN) bash

# Converte um PDF com o Docling para o cache (ADR 008 §4), por faixas de
# páginas (RANGE, padrão 40). Cada faixa é um processo separado — a memória é
# liberada entre faixas, então o livro inteiro cabe na VM sem aumentá-la.
# Cada faixa vira pages_XXXX-YYYY.json; a junção é feita no ingest (nível dos
# MdBlocks, com página absoluta). Pula faixas já convertidas.
RANGE = 40
docling:
ifndef PDF
	$(error uso: make docling PDF=<arquivo em data/raw>)
endif
	@dir=$$($(COMPOSE) run --rm -T app python -m map_relations prepare /app/data/raw/$(name)); \
	ranges=$$($(COMPOSE) run --rm -T app python -m map_relations docling-ranges /app/data/raw/$(name) --size $(RANGE)); \
	mkdir -p "$$dir"; \
	for r in $$ranges; do \
		s=$$(printf '%04d' $${r%-*}); e=$$(printf '%04d' $${r#*-}); \
		out="$$dir/pages_$$s-$$e.json"; \
		if [ -f "$$out" ]; then echo "faixa $$r: cache ok"; continue; fi; \
		echo "== faixa $$r =="; \
		$(COMPOSE) --profile docling run --rm docling sh -c \
			"/usr/bin/time -v docling convert /data/raw/$(name) --to json $(DOCLING_FLAGS) \
			 --page-range $$r --output /$$dir 2> /$$dir/time-$$r.txt; \
			 mv /$$dir/$(stem).json /$$dir/pages_$$s-$$e.json; \
			 grep 'Maximum resident set size' /$$dir/time-$$r.txt"; \
		rm -f "$$dir/time-$$r.txt"; \
	done

# Compara pdf_loader × Docling; grava data/processed/<hash>/comparacao_docling.md
compare: docling
	$(RUN) python -m map_relations compare /app/data/raw/$(name)

# Roda a comparação para todos os PDFs listados em eval/pdfs/conjunto.txt
compare-all:
	@grep -vE '^\s*(#|$$)' eval/pdfs/conjunto.txt | while read -r pdf; do \
		echo "== $$pdf =="; \
		$(MAKE) --no-print-directory compare PDF=$$pdf || exit 1; \
	done

# Lista pastas órfãs de data/processed/ (APPLY=1 remove de verdade)
clean-processed:
	$(RUN) python -m map_relations clean $(if $(APPLY),--apply,)

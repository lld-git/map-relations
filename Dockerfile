# Multi-stage: base (comum) -> prod (execução) -> dev (prod + ferramentas).
# O Docling fica no serviço próprio (B04b), não nesta imagem.
# map_relations é pacote instalável (hatchling, ADR 007): sem PYTHONPATH.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # venv na frente do PATH: "python -m map_relations" funciona sem uv run
    PATH="/app/.venv/bin:$PATH"

# Apply fixes for CVE-2026-76844 and CVE-2026-85091 (zlib1g HIGH) — see docs/adr/001
RUN apt-get update && apt-get install -y --only-upgrade zlib1g && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock ./

# ── prod: dependências de execução e modelo spaCy, sem ferramentas de dev ─────

FROM base AS prod

# 1ª passada só com dependências (cache de camada até o lockfile mudar).
# pt-core-news-sm está declarado como dependência URL em pyproject.toml.
RUN uv sync --frozen --no-dev --no-install-project

RUN useradd --create-home --uid 1000 appuser

COPY --chown=appuser:appuser . .

# 2ª passada instala o próprio pacote, não editável (código vai para site-packages).
# data/ e eval/runs/ são excluídos do contexto Docker (.dockerignore) e montados
# como volumes em dev; criamos os diretórios aqui para que testes sem volumes passem.
RUN uv sync --frozen --no-dev --no-editable && \
    mkdir -p data/raw data/processed eval/runs && \
    chown -R appuser:appuser /app/.venv /app/data /app/eval/runs && \
    chown appuser:appuser /app

USER appuser

# ── dev: prod + grupo dev (pytest, ruff, mypy, pydeps, vulture) + graphviz ────

FROM prod AS dev

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends graphviz pandoc && \
    rm -rf /var/lib/apt/lists/*

# Reinstala com grupo dev e o pacote em modo editável (código vivo nos volumes)
RUN uv sync --frozen && chown -R appuser:appuser /app/.venv

USER appuser

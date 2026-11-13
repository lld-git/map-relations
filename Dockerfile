# Multi-stage: base (comum) -> prod (execução) -> dev (prod + ferramentas).
# O Docling fica no serviço próprio (B04b), não nesta imagem.

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # permite "python -m map_relations" (o pacote vive em research/)
    PYTHONPATH=/app/research

# Apply fixes for CVE-2026-76844 and CVE-2026-85091 (zlib1g HIGH) — see docs/adr/001
RUN apt-get update && apt-get install -y --only-upgrade zlib1g && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

WORKDIR /app

COPY pyproject.toml uv.lock ./

# ── prod: dependências de execução e modelo spaCy, sem ferramentas de dev ─────

FROM base AS prod

# pt-core-news-sm está declarado como dependência URL em pyproject.toml,
# então uv sync instala o modelo junto com tudo o mais.
RUN uv sync --frozen --no-dev

# Non-root user; chown .venv (onde o modelo fica) e /app (para caches)
RUN useradd --create-home --uid 1000 appuser && \
    chown -R appuser:appuser /app/.venv && \
    chown appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

# ── dev: prod + grupo dev (pytest, ruff, mypy, pydeps, vulture) + graphviz ────

FROM prod AS dev

USER root

RUN apt-get update && \
    apt-get install -y --no-install-recommends graphviz && \
    rm -rf /var/lib/apt/lists/*

RUN uv sync --frozen && chown -R appuser:appuser /app/.venv

USER appuser

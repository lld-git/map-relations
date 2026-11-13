FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Apply fixes for CVE-2026-76844 and CVE-2026-85091 (zlib1g HIGH) — see docs/adr/001
RUN apt-get update && apt-get install -y --only-upgrade zlib1g && rm -rf /var/lib/apt/lists/*

RUN pip install uv --no-cache-dir

WORKDIR /app

# Install Python dependencies — cached until lockfile changes
COPY pyproject.toml uv.lock ./
# pt-core-news-sm está declarado como dependência URL em pyproject.toml,
# então uv sync instala o modelo junto com tudo o mais.
RUN uv sync --frozen

# Non-root user; chown .venv (onde o modelo fica) e /app (para pytest cache)
RUN useradd --create-home --uid 1000 appuser && \
    chown -R appuser:appuser /app/.venv && \
    chown appuser:appuser /app

# Copy source code owned by appuser (overrides pyproject.toml/uv.lock from above)
COPY --chown=appuser:appuser . .

USER appuser

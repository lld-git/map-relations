# Serviço Docling (B04b) — conversão estruturada de PDF.
# Imagem pesada (torch + modelos de layout); fica fora do CI, só no
# profile "docling" do Compose.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Versão pinada — a chave de cache em map_relations/ingest/store.py
# (DOCLING_VERSION) precisa acompanhar qualquer mudança aqui.
# docling-core também fixado (2.150.0 só pede >=2.106.0,<3.0.0, sem lock):
# mesma versão exata do dev-dependency do app (pyproject.toml), para o
# mapa de rótulos (DOCLING_LABEL_MAP) não divergir do que o serviço usa.
RUN pip install --no-cache-dir docling==2.150.0 docling-core==2.107.1

# /usr/bin/time -v para medir tempo e memória das conversões (ADR 008)
RUN apt-get update && apt-get install -y --no-install-recommends time && \
    rm -rf /var/lib/apt/lists/*

# Baixa os modelos de layout no build: o contêiner roda offline depois.
# DOCLING_ARTIFACTS_PATH aponta o CLI para o cache do build (sem download em runtime).
RUN docling-tools models download
ENV DOCLING_ARTIFACTS_PATH=/root/.cache/docling/models

WORKDIR /data

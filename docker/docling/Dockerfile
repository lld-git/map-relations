# Serviço Docling (B04b) — conversão estruturada de PDF.
# Imagem pesada (torch + modelos de layout); fica fora do CI, só no
# profile "docling" do Compose.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir docling

# Baixa os modelos de layout no build: o contêiner roda offline depois.
# DOCLING_ARTIFACTS_PATH aponta o CLI para o cache do build (sem download em runtime).
RUN docling-tools models download
ENV DOCLING_ARTIFACTS_PATH=/root/.cache/docling/models

WORKDIR /data

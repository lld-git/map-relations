# Serviço MinerU (B04d, fase 6, B.3) — reconhecimento do MinerU Basic, sem
# adaptador: só para rodar uma vez sobre o PDF de teste e registrar em ADR os
# campos reais da saída. Fica fora do CI, só no profile "mineru" do Compose,
# igual ao serviço docling (B04b).

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Versão pinada (ADR do B04d fase 6). Sem extra: usa o backend "pipeline"
# (ONNX, CPU) por padrão — é o que o plano chama de "MinerU Basic".
RUN pip install --no-cache-dir mineru==4.2.3

# /usr/bin/time -v para medir tempo e pico de memória (mesma técnica do
# serviço docling, ADR 008).
RUN apt-get update && apt-get install -y --no-install-recommends time && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /data

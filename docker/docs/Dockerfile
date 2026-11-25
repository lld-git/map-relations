# Serviço de documentação (Zensical, não MkDocs com o tema Material).
# Só sobe com --profile docs (make docs); nunca no CI. Versão exata fixada.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir zensical==0.1.3

WORKDIR /project

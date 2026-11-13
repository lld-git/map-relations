# Mapa de Relações

Transforma documentos em um dossiê navegável de pessoas, relações, provas, linha do tempo e notas.

## Setup

```bash
uv sync
uv run python -m spacy download pt_core_news_sm
```

## Comandos

```bash
uv run pytest          # testes
uv run ruff check .    # lint
uv run mypy research tests  # tipos
```

Ver `CLAUDE.md` para o plano completo de blocos e decisões de arquitetura.

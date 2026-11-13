# Mapa de Relações

Transforma documentos em um dossiê navegável de pessoas, relações, provas, linha do tempo e notas.

## Requisitos

- Docker + Docker Compose ≥ 2.24 (para `env_file.path` e `env_file.required`)
- Git

Nenhuma dependência Python instalada na máquina host.

## Setup

```bash
cp .env.example .env   # adicione as chaves de API que forem usar
docker compose build
```

## Comandos

```bash
docker compose run --rm app uv run pytest                 # testes
docker compose run --rm app uv run ruff check .           # lint
docker compose run --rm app uv run mypy research tests    # tipos
docker compose up painel                                  # painel de desenvolvimento (B02b)
```

## Chaves de API

Coloque as chaves em `.env` (nunca commitado). O arquivo `.env.example` lista as variáveis esperadas.

Ver `CLAUDE.md` para o plano completo de blocos e decisões de arquitetura.

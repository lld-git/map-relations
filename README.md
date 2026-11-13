# Map Relations

Transforms documents into a navigable dossier of people, relations, evidence,
a timeline, and notes. This phase researches the method in Python
(see `CLAUDE.md` for the block plan and `docs/architecture.md` for the architecture).

## About

A web application that extracts entities and relationships from plain-text
documents and organises them into a structured, evidence-linked dossier.
Designed with no vendor lock-in: no proprietary graph database or cloud
dependency required. The AI engine is pluggable (any OpenAI-compatible
provider or local model). The end product runs almost entirely in the browser
to keep fixed costs near zero. The TypeScript port happens only after C2.

## Requirements

- Docker + Docker Compose ≥ 2.24 (for `env_file.path` and `env_file.required`)
- GNU Make
- Git

No Python dependency installed on the host machine: everything runs in Docker
(principle 13 in CLAUDE.md).

## Setup

```bash
cp .env.example .env   # fill in only the API keys you plan to use
docker compose build
```

`.env` is never committed; `.env.example` lists the expected variables
(MISTRAL_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY).

## Document storage

Place files in `data/raw/` (ignored by Git) — PDF, TXT, EPUB, DOCX, or HTML.
Ingestion (ADR 008) writes to `data/processed/<file_hash>/`:

- `documento.md` — **the Markdown source you review and edit**
- `docling/<version>-<options>/docling.json` — conversion cache (1× per PDF)
- `canonical.txt`, `ingest.json`, `report.md` — derived from the `.md`

Integrity rule: editing `documento.md` changes the canonical hash — rerun
`make ingest` (cheap) before filling in gold labels.

## Commands (Makefile)

All targets run inside the container via `docker compose`.

| Target | What it does |
|---|---|
| `make test` | pytest |
| `make lint` | ruff |
| `make typecheck` | mypy on research, tests, and scripts |
| `make schema-check` | fails if JSON Schemas in contracts/ are out of date |
| `make check` | lint + typecheck + schema-check + test |
| `make ingest PDF=<file>` | document from `data/raw/` → `data/processed/<hash>/` (runs Docling if cache is missing) |
| `make map` | generates `docs/mapa/imports.svg` (pydeps) and `docs/mapa/codigo_morto.txt` (vulture) |
| `make shell` | bash shell inside the container |
| `make docling PDF=<file>` | fills the Docling cache in page ranges (`RANGE=40`; skips completed ranges) |
| `make compare PDF=<file>` | compares pdf_loader × Docling → `comparacao_docling.md` |
| `make compare-all` | compares all PDFs listed in `eval/pdfs/conjunto.txt` |
| `make clean-processed` | lists orphan folders in `data/processed/` (`APPLY=1` removes them) |

Ingestion example (output is illustrative):

```bash
cp ~/Downloads/my-document.pdf data/raw/
make ingest PDF=my-document.pdf
# file hash:      3f2a…
# canonical hash: 9c81…
# output: /app/data/processed/3f2a…
# quality: 230 pages, 412 paragraphs, 10 chapters, 460 items removed, 0 alerts
```

After that, review `data/processed/<hash>/documento.md` (remove paratext, fix
titles) and run `make ingest` again — the review is never overwritten
(only with `--force-md` on the CLI).

The development panel (B02b, not yet implemented) will start with
`docker compose up painel` at `127.0.0.1:8010`.

## Documentation

- `docs/architecture.md` — layers, contracts, and ADRs
- `docs/mapa/fluxo.md` — data flow (the single flow diagram)
- `docs/mapa/arquivos.md` — role and status of each .py file
- `docs/status.md` — current state and handoff
- `docs/phases.md` — metrics and learnings per phase
- `docs/blocks/` — completion report for each block with human review

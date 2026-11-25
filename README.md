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

## About

Map Relations turns long documents into an explorable relationship dossier:
people, relations, timelines and notes, with every extracted relation linked to
literal evidence in the source text. It is intended for commentators, content
creators and researchers who need to explain connections and cite their sources.

### Why it is hard
Entity resolution, implicit relations, temporal context and false positives from
LLMs. The approach is multi-pass extraction with deterministic checks, blind
verification and a measured comparison against single-prompt baselines.

### Current stage (research, in Python)
Done:
- Docker-first environment, CI, tests, type checking and a generated project map.
- Generic domain model (people, groups, places, objects and events; claims,
  participation, evidence and audit log), with stable keys for reprocessing and
  a state machine that never lets automated runs overwrite human decisions.
- Document ingestion with a single contract: PDF converted with Docling (page
  ranges in separate processes, cached) or a lightweight fallback, normalized to
  reviewable Markdown and then to a canonical text with character offsets,
  paragraphs, chapters and a quality report.

Next: evaluation harness with a hand-annotated gold set, model adapters, and the
first extraction pipeline.

### Roadmap
- V1: one public-domain literary work; relations with literal evidence, explored
  through a graph, timeline and report.
- V2: events and how characters take part in them, incremental knowledge over the
  story, user corrections and user-guided deeper extraction.
- Later: newspapers and magazines, multiple sources over time, source tracking,
  contradiction detection and safeguards for real people.

### How I work with AI
I define architecture, decisions (ADRs) and acceptance criteria. An AI coding
assistant plans and implements one block at a time; I review plans, tests and
results before moving on. Every block is documented in `docs/blocks/`.

### Stack
Python 3.12, uv, Pydantic, spaCy, Docling, NetworkX, pytest, ruff, mypy, Docker
Compose. A browser version in TypeScript is planned after the method is validated.

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
| `make schema-check` | fails if JSON Schemas or the relation ontology artifacts (contracts/ontology/) are out of date, or if relations.yaml is invalid |
| `make check` | lint + typecheck + schema-check + test |
| `make ci` | reproduces both jobs of `.github/workflows/ci.yml` locally (images built from the Git index, so `git add` first; no volumes, non-root); `tests/test_ci_sync.py` fails if it drifts from `ci.yml` |
| `make ingest PDF=<file>` | document from `data/raw/` → `data/processed/<hash>/` (runs Docling if cache is missing) |
| `make gold-fill GOLD=<file> OUT=<new file>` | `gold fill-offsets`: rebuilds every evidence anchor against the current canonical text (all or nothing; `OUT` ≠ `GOLD`; optional `REPORT=<json>`) |
| `make gold-convert DRAFT=<file> OUT=<new file>` | `gold convert-draft`: one-off conversion of the legacy draft into a gold file (all or nothing; the draft is never touched) |
| `make gold-validate GOLD=<file>` | `gold validate`: checks a gold file against the ontology and the current canonical text |
| `make eval RUN=<run.json> GOLD=<gold.json> [CANONICAL=<canonical.txt>] [TRACK=1]` | `eval`: scores a run against the gold file (strict and relaxed measures, attribution, parent-type hits, control pairs, embedded text) → `eval/reports/<run_id>/report.{json,md}` (git-ignored). `TRACK=1` also logs numbers to MLflow. No default path to `data/golden/` |
| `make mlflow` / `make mlflow-stop` | starts/stops the local MLflow server (`http://127.0.0.1:5010`, data in `./mlflow_data/`, git-ignored); the tracker refuses any address outside this machine |
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

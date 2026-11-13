# Mapa de Relações

Transforma documentos em um dossiê navegável de pessoas, relações, provas,
linha do tempo e notas. Fase atual: pesquisa do método em Python
(ver `CLAUDE.md` para o plano de blocos e `docs/architecture.md` para a arquitetura).

## Requisitos

- Docker + Docker Compose ≥ 2.24 (para `env_file.path` e `env_file.required`)
- GNU Make
- Git

Nenhuma dependência Python instalada na máquina host: tudo roda em Docker
(princípio 13 do CLAUDE.md).

## Configuração

```bash
cp .env.example .env   # preencha só as chaves de API que for usar
docker compose build
```

O `.env` nunca é commitado; o `.env.example` lista as variáveis esperadas
(MISTRAL_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY).

## Onde colocar os documentos

Em `data/raw/` (ignorado pelo Git) — PDF, TXT, EPUB, DOCX ou HTML. A ingestão
(ADR 008) grava em `data/processed/<hash_do_arquivo>/`:

- `documento.md` — **fonte em Markdown, que você revisa e edita**
- `docling/<versão>-<opções>/docling.json` — cache da conversão cara (1× por PDF)
- `canonical.txt`, `ingest.json`, `report.md` — derivados do `.md`

Regra de integridade: editar `documento.md` muda o hash canônico — rode
`make ingest` de novo (barato) e só depois preencha gabaritos.

## Comandos (Makefile)

Todos os alvos rodam dentro do contêiner via `docker compose`.

| Alvo | O que faz |
|---|---|
| `make test` | pytest |
| `make lint` | ruff |
| `make typecheck` | mypy em research, tests e scripts |
| `make schema-check` | falha se os JSON Schemas de contracts/ estiverem desatualizados |
| `make check` | lint + typecheck + schema-check + test |
| `make ingest PDF=<arquivo>` | documento de `data/raw/` → `data/processed/<hash>/` (roda o Docling se faltar cache) |
| `make map` | gera `docs/mapa/imports.svg` (pydeps) e `docs/mapa/codigo_morto.txt` (vulture) |
| `make shell` | shell bash dentro do contêiner |
| `make docling PDF=<arquivo>` | preenche o cache Docling por faixas de página (`RANGE=40`; pula faixas prontas) |
| `make compare PDF=<arquivo>` | compara pdf_loader × Docling → `comparacao_docling.md` |
| `make compare-all` | compara todos os PDFs listados em `eval/pdfs/conjunto.txt` |
| `make clean-processed` | lista pastas órfãs de `data/processed/` (`APPLY=1` remove) |

Exemplo de ingestão:

```bash
cp ~/Downloads/o-processo.pdf data/raw/
make ingest PDF=o-processo.pdf
# hash do arquivo: 3f2a…
# hash canônico:   9c81…
# saída: /app/data/processed/3f2a…
# qualidade: 230 páginas, 412 parágrafos, 10 capítulos, 460 itens removidos, 0 alertas
```

Depois revise `data/processed/<hash>/documento.md` (apague paratexto, corrija
títulos) e rode `make ingest` de novo — a revisão nunca é sobrescrita
(só com `--force-md` na CLI).

O painel de desenvolvimento (B02b, ainda não implementado) subirá com
`docker compose up painel` em `127.0.0.1:8010`.

## Documentação

- `docs/architecture.md` — camadas, contratos e ADRs
- `docs/mapa/fluxo.md` — fluxo de dados (único diagrama de fluxo)
- `docs/mapa/arquivos.md` — papel e status de cada arquivo .py
- `docs/status.md` — estado atual e handoff
- `docs/phases.md` — métricas e aprendizados por fase
- `docs/blocks/` — relatório de conclusão de cada bloco com revisão humana

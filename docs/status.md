# Status — atualizado em 2026-11-10

## Concluído
- **B00** — fundação: projeto Python (uv), pytest, ruff, mypy, CI com 3 jobs.
- **B00b** — Docker: Dockerfile (appuser UID 1000), docker-compose.yml
  (app, painel em 127.0.0.1:8010, docling-stub), .dockerignore, .env.example.
  116 testes passam em `docker compose run --rm app uv run pytest`.
- **B01** — core e contratos:
  - `core/models.py`: 15 modelos Pydantic (snake_case + alias camelCase,
    `populate_by_name`), enums StrEnum, validadores de offsets, confidence e level.
  - `core/ids.py`: `new_id` (UUIDv4), `nfc`, chaves de conteúdo `claim_key`,
    `participation_key`, `evidence_key` (ADR 003).
  - `core/states.py`: tabela de transições do ADR 006 (`validate_transition`,
    `can_transition`, `is_terminal`, `InvalidTransition`).
  - `core/rules.py`: `validate_claim_kinds` (subjectKinds/objectKinds) e
    `transition` que gera ChangeLog com actor e run_id/pass_id.
  - `core/protocols.py`: LlmEngine (complete assíncrono), SourceConnector,
    DocumentParser, ProjectStore; erros tipados do motor.
  - `scripts/generate_schemas.py`: gera 15 JSON Schemas em contracts/schemas;
    `--check` no CI falha se desatualizado.
  - Testes parametrizados de todos os 5×5×2 pares de transição.

## Em andamento
- Nada — B01 aguarda revisão do Leon antes do B02.

## Decisões recentes (com link para o ADR)
- [ADR 001](adr/001-cves-imagem-base.md) — CVEs da imagem base: 2 zlib1g
  corrigidos no Dockerfile, 47 aceitos sem fix disponível.
- [ADR 002](adr/002-docker-desktop-permissoes.md) — Docker Desktop: `user: "0:0"`
  no compose local; appuser continua padrão da imagem (CI/deploy).
- [ADR 003](adr/003-ids-estaveis.md) — UUID como identidade + chaves de
  conteúdo (claim_key, participation_key, evidence_key) para upsert.
- [ADR 004](adr/004-offsets-nfc.md) — offsets em code points sobre texto NFC;
  content_hash sobre a mesma representação.
- [ADR 005](adr/005-llm-assincrono.md) — só LlmEngine.complete é async; camada
  de tarefa usa gather + semáforo; nada de asyncio.run por chamada.
- [ADR 006](adr/006-transicoes-de-estado.md) — tabela de transições; auto move
  entre estados automáticos; humano decide estados humanos; toda mudança gera
  ChangeLog.

## Pendências
- Criar repositório remoto no GitHub (map-relations) — aguardando conta do Leon.
- B02: eval/gold/processo.json e comando eval (não iniciado, sem persistência ainda).

## Próximo passo
Revisão do B01 pelo Leon; depois B02 (avaliação).

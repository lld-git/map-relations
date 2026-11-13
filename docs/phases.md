# Fases e checkpoints

Uma seção por fase e checkpoint: objetivo, métricas, observações e
aprendizados. Só métricas que existem de verdade; sem números inventados.
Atualizado em 2026-11-11.

## B00 — Fundação (concluído em 2026-11-05)

**Objetivo:** projeto Python com uv, comandos de teste/lint/typecheck e CI verde
com um teste real.

**Métricas:** CI com 1 job no início; testes iniciais de ingestão (Source,
hash) e NER.

**Observações:** código de ingestão adaptado do projeto Grafo; marker
`requires_spacy_model` separa testes que precisam do modelo pt.

**Aprendizados:** hash da fonte deve ser do texto normalizado, não dos bytes
brutos — corrigido junto ao B00b; `eval/` não deve ser pacote Python.

## B00b — Docker (concluído em 2026-11-10)

**Objetivo:** tudo em contêiner; testes passam em máquina sem Python.

**Métricas:** 11 testes passando em Docker na conclusão; Trivy: 49 CVEs HIGH,
0 CRITICAL na imagem base — 2 com fix aplicado (zlib1g), 47 aceitos (ADR 001).

**Observações:** modelo spaCy como dependência URL no pyproject.toml, para o
lockfile gerenciá-lo; porta do painel só em 127.0.0.1.

**Aprendizados:** `uv sync --frozen` desinstala o que não está no lockfile —
o modelo precisa ser dependência declarada; no Docker Desktop para Linux,
volumes aparecem como root no contêiner (ADR 002); bind de arquivo único
impede rename atômico do uv — montar o diretório.

## B01 — Core e contratos (concluído em 2026-11-11)

**Objetivo:** modelos Pydantic, IDs estáveis, transições de estado, Protocols
e JSON Schemas gerados.

**Métricas:** 116 testes na conclusão; 15 modelos; 15 JSON Schemas com
verificação `--check` no CI; 50 pares de transição testados (5 estados × 5
estados × 2 atores).

**Observações:** proposta revisada pelo Leon antes da implementação, com 9
ajustes (chaves de upsert, ChangeLog com actor, enums adicionais, validadores).

**Aprendizados:** `class` é palavra reservada — campo `claim_class` com alias
`"class"` no JSON; separador `\x00` nas chaves de conteúdo evita colisão por
justaposição; StrEnum simplifica serialização.

## B04 — Contrato de ingestão, parte antecipada (concluído em 2026-11-11)

**Objetivo:** IngestResult com texto canônico NFC, mapa de parágrafos,
locate(offset) → "cap. X, § Y" e relatório de revisão humana.

**Métricas:** 137 testes na conclusão (21 do contrato de ingestão); critério
"parágrafo devolvido contém o trecho citado" coberto por teste.

**Observações:** antecipado antes do B02 porque os offsets do gabarito
referenciam o texto canônico. TXT/EPUB e url_loader ficam para o resto do bloco.

**Aprendizados:** linhas em branco precisam sobreviver à limpeza de página
(estrutura de parágrafos); título de capítulo colado ao texto exige isolamento
explícito; parágrafo que cruza página sem hífen vira dois — fica para o
Docling (B04b).

## B04-docs — Documentação, CLI e mapa (concluído em 2026-11-11)

**Objetivo:** CLI de ingestão, Dockerfile multi-stage (prod/dev), Makefile,
README, architecture.md e mapa do projeto gerado por ferramenta.

**Métricas:** 139 testes na conclusão; vulture (confiança ≥ 60%): 8 candidatos,
sendo 7 contratos usados só em testes e 1 dívida real (url_loader);
pydeps: 14 módulos no grafo de imports.

**Observações:** `--cluster` do pydeps colapsa tudo no pacote `research`, então
o mapa usa módulos individuais com `--rmprefix`.

**Aprendizados:** whitelist do vulture por categoria (campos Pydantic, métodos
de Protocol, membros de enum) mantém o codigo_morto.txt com sinal, não ruído.

## B04-pkg — Pacote instalável (concluído em 2026-11-11)

**Objetivo:** `import map_relations` sem PYTHONPATH; editável na dev, não
editável na prod.

**Métricas:** 139 testes na conclusão; 41 nós no imports.svg; CLI verificada
nas imagens dev e prod.

**Observações:** hatchling com `packages = ["research/map_relations"]` mantém a
pasta research/; CI com cache de camadas GHA.

**Aprendizados:** dependência por URL exige `allow-direct-references` no
hatchling; venv precisa estar no PATH da imagem para `python -m` funcionar sem
`uv run`; caminho de dados não pode derivar de `__file__` quando o pacote vai
para site-packages; config montada no contêiner evita rebuild a cada ajuste
de ruff/mypy/pytest.

## B04b-prova — Correções genéricas e prova do Docling (concluído em 2026-11-12)

**Objetivo:** corrigir de forma genérica os problemas vistos no O Processo
(letras espaçadas, numeração fora da obra, capítulos vazios) e medir o Docling
contra o pdf_loader no mesmo PDF antes de decidir o B04b.

**Métricas:** O Processo: 24 "capítulos" errados → 10 corretos. Docling sem
OCR: 61 s para 40 páginas (~1,5 s/página) na CPU; OOM com as 379 páginas na
VM de 3,7 GiB do Docker Desktop. Na fatia de 40 páginas: títulos explícitos
1 (pdf_loader) × 0 (Docling); blocos de texto 43 × 125; cabeçalhos/rodapés
37 removidos por repetição × 0 rotulados pelo Docling; 1 parágrafo
atravessando página detectado pelo Docling. 149 testes na conclusão.

**Observações:** títulos explícitos têm precedência sobre a regra de
maiúsculas; sem nenhum explícito, maiúsculas numeram com alerta. Nenhuma regra
específica de livro.

**Aprendizados:** a regra de maiúsculas sozinha transforma folha de rosto,
sinopse e subtítulos em capítulos; precedência resolve sem lista de exceções.

## Checkpoint C1 — comparativo A/B/C (não iniciado)

Fecha com o relatório do B06: regras vs. LLM vs. híbrido contra o gabarito.

## Checkpoint C1b — teste por níveis (não iniciado)

Fecha com o B08: N2 a N5 medidos, 5 achados com provas.

## Checkpoint C2 — dossiê e percepção (não iniciado)

Fecha com o B09: dossiê com dados fixos e teste de percepção. Só depois dele
começa o porte para TypeScript (B10+).

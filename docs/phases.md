# Fases e checkpoints

Uma seção por fase e checkpoint: objetivo, métricas, observações e
aprendizados. Só métricas que existem de verdade; sem números inventados.
Atualizado em 2026-11-21.

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

**Objetivo:** corrigir de forma genérica os problemas vistos no documento de teste
(letras espaçadas, numeração fora da obra, capítulos vazios) e medir o Docling
contra o pdf_loader no mesmo PDF antes de decidir o B04b.

**Métricas:** Documento de teste: 24 "capítulos" errados → 10 corretos. Docling sem
OCR: 61 s para 40 páginas (~1,5 s/página) na CPU; OOM com as 379 páginas na
VM de 3,7 GiB do Docker Desktop. Na fatia de 40 páginas: títulos explícitos
1 (pdf_loader) × 0 (Docling); blocos de texto 43 × 125; cabeçalhos/rodapés
37 removidos por repetição × 0 rotulados pelo Docling; 1 parágrafo
atravessando página detectado pelo Docling. 149 testes na conclusão.

**Observações:** títulos explícitos têm precedência sobre a regra de
maiúsculas; sem nenhum explícito, maiúsculas numeram com alerta. Nenhuma regra
específica de livro.

**Aprendizados:** a regra de maiúsculas sozinha transforma folha de rosto,
paratexto e subtítulos em capítulos; precedência resolve sem lista de exceções.

## B04c — Markdown intermediário único (concluído em 2026-11-12)

**Objetivo:** ADR 008 — conversores por formato geram documento.md revisável;
parser único → IngestResult; Docling 1× por documento com cache por
versão+opções; layout data/processed/<hash_do_arquivo>/.

**Métricas:** 165 testes na conclusão. Medição Docling na fatia de 40 páginas
(VM 3,7 GiB): padrão 84,4 s / pico 3,05 GiB; com OCR, tabelas e imagens
desligados 64,2 s / 2,32 GiB (−24% tempo, −22% memória). O pico de ~3 GiB do
modo padrão explica o OOM do documento de 379 páginas.

**Observações:** documento.md nunca é sobrescrito sem --force-md;
conversao.json preserva removidos e alertas da conversão para reparses;
editar o .md muda o hash canônico (coberto por teste).

**Aprendizados:** o escape mínimo (\\#, \\*, <\\!--) basta porque o parser só
interpreta a convenção; manter a chave de cache em código e as flags no
Makefile exige nota de sincronia dos dois lados.

### Ajustes pós-revisão (2026-11-13)

- **Alertas sobre o .md atual:** quality.alerts passa a vir só do parser sobre
  o documento.md atual; os alertas da conversão ficam numa seção à parte e são
  marcados resolvidos quando o .md editado não os reproduz (edição detectada
  por hash do .md gravado em conversao.json).
- **Conversão por faixas:** o Docling converte em faixas de 40 páginas, cada
  uma num processo separado. `DoclingDocument.concatenate` renumera as páginas
  (descartado); a junção é feita nos MdBlocks, com página absoluta e a regra de
  parágrafo que atravessa a fronteira. **O documento de teste inteiro (379 p.) converteu
  em 10 faixas com pico de 2,12–2,45 GiB por faixa** (antes: OOM num processo
  só na VM de 3,7 GiB) → 378 p., 1113 parágrafos, 9 capítulos, sem OOM.
- **Aprendizado:** a classificação de títulos tem de ser global (depois da
  junção), senão um capítulo explícito numa faixa posterior não rebaixa
  maiúsculas de uma faixa anterior.

## B02a — Ontologia de relações (concluído em 2026-11-21)

**Objetivo:** tipos de relação estáveis (YAML versionado, trava de ids), `claim_key`
única lida do `RelationType`, `new_claim` como único caminho de criação, classe
`alegada` com `asserted_by` e `narrative_scope`, antes do gabarito do B02.

**Métricas:** 270 testes na conclusão (50 novos no bloco); 12 tipos anotáveis e
5 abstratos; 4 artefatos gerados conferidos em `make schema-check` e no CI.

**Observações:** `vigia` renomeado para `exerce_vigilancia_sobre` antes de publicar
a trava; disjunção é alerta e irreflexividade é rejeição (D5); gabarito da obra
protegida fica em `data/golden/`, fora do Git.

**Aprendizados:** `ids` precisa importar `RelationType` só para tipagem
(`TYPE_CHECKING`), porque `models` já importa `ids`.

## Checkpoint C1 — comparativo A/B/C (não iniciado)

Fecha com o relatório do B06: regras vs. LLM vs. híbrido contra o gabarito.

## Checkpoint C1b — teste por níveis (não iniciado)

Fecha com o B08: N2 a N5 medidos, 5 achados com provas.

## Checkpoint C2 — dossiê e percepção (não iniciado)

Fecha com o B09: dossiê com dados fixos e teste de percepção. Só depois dele
começa o porte para TypeScript (B10+).

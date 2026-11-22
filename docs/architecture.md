# Arquitetura

Atualizado em 2026-11-21 (B02a, ontologia). Este documento descreve o que
existe no código; o planejado aparece tracejado nos diagramas e marcado como
planejado. O único diagrama de fluxo do projeto está em
[docs/mapa/fluxo.md](mapa/fluxo.md).

## Camadas

| Camada | Pasta | Papel | Regra |
|---|---|---|---|
| Contratos | `contracts/` | JSON Schema, prompts, lentes e casos — independentes de linguagem | Gerados de `core/models.py`; nunca editados à mão |
| Domínio | `research/map_relations/core/` | Modelos Pydantic, IDs, transições de estado, regras e Protocols | Sem dependência de fornecedor; síncrono e puro (ADR 005) |
| Camada comum de layout | `research/map_relations/ingest/layout.py` | `LayoutItem`/`BBox` e pós-processamento comum: junção de parágrafo entre páginas/faixas, precedência de títulos, cabeçalho/rodapé por repetição, faixa do corpo | Escrita uma vez para todos os conversores (ADR 009); dataclass, nunca em `contracts/schemas` |
| Conversores | `research/map_relations/ingest/convert_*.py`, `canonical.py` | formato de origem → `LayoutItem[]` → blocos do Markdown intermediário | Só eles conhecem o formato de origem (ADR 008); decisão de layout fica na camada comum (ADR 009) |
| Parser único | `research/map_relations/ingest/markdown.py` | documento.md → IngestResult | Interpreta só a convenção; o resto é literal |
| Armazenamento | `research/map_relations/ingest/store.py` | layout `data/processed/<hash>/`, cache Docling, órfãs | O nome da pasta usa o hash do arquivo de origem |
| CLI | `research/map_relations/__main__.py` | ingest, prepare, compare, clean | Só orquestra; sem lógica de domínio |
| Ontologia | `contracts/ontology/`, `core/ontology*.py`, `ontology_io.py` | `relations.yaml` (fonte) → `Ontology`, trava de ids e artefatos gerados | Modelos puros em `core`; leitura de YAML só em `ontology_io` (ADR 011) |
| Gabarito | `research/map_relations/evaluation/gold.py`, `contracts/schemas/gold.schema.json` | `GoldFile`, `Anchor` (exact/prefix/suffix + offsets) e `validate_gold` contra ontologia e canônico; `anchoring.py`/`fill_offsets.py` (âncora sem chute, tudo ou nada), `convert_draft.py` e os subcomandos `gold ...` (`gold_cli.py`) | Fora do domínio; o gabarito real vive em `data/golden/`, fora do Git (ADR 012) |
| Scripts | `scripts/` | Geração/verificação de schemas e da ontologia | Rodam só em Docker |
| Testes | `tests/` | pytest, tudo em Docker | Não importam fornecedores diretamente |

Pastas previstas na estrutura e ainda vazias (planejado): `engines/`, `tasks/`,
`segment/`, `pipeline/`, `verify/`, `resolve/`, `analysis/`, `compose/` e o
painel (B02b). `nlp/` tem NER usado só em testes até o B05.

O código vive em `research/map_relations/` mas instala como pacote
`map_relations` (hatchling; editável na imagem dev, não editável na prod) —
imports são sempre `map_relations.*`, sem PYTHONPATH
([ADR 007](adr/007-pacote-instalavel.md)).

## Contratos

### Modelo de domínio (`core/models.py`)

15 modelos Pydantic — entity, alias, mention, relationType, source, segment,
claim, participation, evidence, timeScope, lens, pass, run, changeLog, note —
com snake_case em Python e alias camelCase no JSON (`populate_by_name`).
Os JSON Schemas em `contracts/schemas/` são gerados por
`scripts/generate_schemas.py`; o CI falha se estiverem desatualizados.

Regras centrais:
- Transições de estado na tabela do [ADR 006](adr/006-transicoes-de-estado.md):
  auto move entre proposta/verificada/rejeitada; humano decide estados humanos;
  estados humanos nunca são alterados por processamento automático.
- Identidade por UUID + chaves de conteúdo para upsert
  ([ADR 003](adr/003-ids-estaveis.md)).
- `validate_claim_kinds` rejeita claims com kind incompatível com o relationType.
- `rules.new_claim` é o único caminho de criação de claim: rejeita tipo abstrato,
  obsoleto e relação de alguém consigo mesmo; disjunção é só alerta
  ([ADR 011](adr/011-ontologia-de-relacoes.md)).
- `claim_key(s, RelationType, o, *, asserted_by, narrative_scope)`: simetria lida do
  tipo; classe fora da chave. Classe `alegada` exige `asserted_by`.
- Toda transição gera ChangeLog com actor e run_id/pass_id (`core/rules.py`).

### IngestResult (`core/ingest_contract.py`)

Saída única da ingestão: texto canônico NFC, lista de parágrafos
(id, sourceId, chapter, number, kind — título/subtítulo/texto —, page,
offsets), capítulos, itens removidos com motivo e página, e QualityReport com
alertas. Offsets em Unicode code points sobre o texto NFC
([ADR 004](adr/004-offsets-nfc.md)). `locate(offset)` devolve "cap. X, § Y" —
referência legível, nunca usada para verificar provas.

Todo formato passa pelo Markdown intermediário
([ADR 008](adr/008-markdown-intermediario.md)): conversores geram
documento.md (fonte revisável pelo humano, com marcadores `<!-- p.N -->`);
o parser único o transforma em IngestResult. Editar o .md muda o hash
canônico e invalida offsets registrados.

### Protocols (`core/protocols.py`)

- `LlmEngine` — id, capabilities, `complete(req)` assíncrono; único ponto
  async do sistema ([ADR 005](adr/005-llm-assincrono.md)). Erros tipados:
  RateLimited, InvalidResponse, AuthError, NetworkError, Aborted.
- `SourceConnector` — lista e busca documentos de uma origem.
- `DocumentParser` — `parse(path) -> IngestResult`. Implementado por
  `PdfParser`; DoclingParser planejado (B04b).
- `ProjectStore` — persistência; sem implementação ainda (planejado).

## Componentes (nível de módulo)

```mermaid
flowchart BT
    subgraph core
        ids["core.ids"]
        models["core.models"]
        contract["core.ingest_contract"]
        states["core.states"]
        rules["core.rules"]
        protocols["core.protocols"]
        ontology["core.ontology"]
        lock["core.ontology_lock"]
    end
    ontoio["ontology_io"]
    genonto["scripts.generate_ontology"]
    subgraph ingest
        document["ingest.document"]
        md["ingest.markdown<br/>(parser único)"]
        layout["ingest.layout<br/>(camada comum)"]
        canonical["ingest.canonical<br/>(rota pdf_loader)"]
        convdocling["ingest.convert_docling"]
        convtxt["ingest.convert_txt"]
        convpandoc["ingest.convert_pandoc"]
        storemod["ingest.store"]
        pdf["ingest.pdf_loader"]
        url["ingest.url_loader"]
        reportmod["ingest.report"]
        dcompare["ingest.docling_compare"]
    end
    cli["__main__ (CLI)"]
    schemas["scripts.generate_schemas"]

    models --> ids
    contract --> ids
    contract --> models
    states --> models
    rules --> models
    rules --> states
    rules --> ontology
    rules --> ids
    ids -.-> models
    ontology --> models
    lock --> ontology
    ontoio --> ontology
    genonto --> ontoio
    genonto --> lock
    cli --> ontoio
    protocols --> contract
    document --> ids
    document --> models
    md --> contract
    md --> document
    layout --> contract
    canonical --> contract
    canonical --> md
    canonical --> layout
    convdocling --> layout
    convdocling --> md
    convtxt --> canonical
    convpandoc --> canonical
    pdf --> canonical
    url --> document
    reportmod --> contract
    dcompare --> layout
    cli --> convdocling
    cli --> convtxt
    cli --> convpandoc
    cli --> storemod
    cli --> pdf
    cli --> reportmod
    cli --> dcompare
    schemas --> models

    mineru["MinerU (reconhecido, ADR 010;<br/>sem adaptador)"]:::planned
    mineru -.-> layout

    engines["engines (B03)"]:::planned
    tasks["tasks (B03)"]:::planned
    painel["painel (B02b)"]:::planned
    docling["DoclingParser (B04b)"]:::planned
    engines -.-> protocols
    tasks -.-> engines
    painel -.-> contract
    docling -.-> contract

    classDef planned stroke-dasharray: 5 5,fill:none
```

O mapa de imports gerado do código real está em
[docs/mapa/imports.svg](mapa/imports.svg) (`make map`); a lista de arquivos com
papel e status está em [docs/mapa/arquivos.md](mapa/arquivos.md).

## ADRs

| ADR | Decisão |
|---|---|
| [001](adr/001-cves-imagem-base.md) | CVEs da imagem base: 2 corrigidos (zlib1g), 47 aceitos sem fix |
| [002](adr/002-docker-desktop-permissoes.md) | Docker Desktop: `user: "0:0"` no compose; appuser padrão da imagem |
| [003](adr/003-ids-estaveis.md) | UUID como identidade; chaves de conteúdo para upsert |
| [004](adr/004-offsets-nfc.md) | Offsets em code points sobre texto NFC |
| [005](adr/005-llm-assincrono.md) | Só LlmEngine.complete é async; tarefas com gather + semáforo |
| [006](adr/006-transicoes-de-estado.md) | Tabela de transições de estado; ChangeLog em toda mudança |
| [007](adr/007-pacote-instalavel.md) | map_relations instalável via hatchling; sem PYTHONPATH |
| [008](adr/008-markdown-intermediario.md) | Markdown intermediário único; cache Docling; documento.md revisável |
| [009](adr/009-camada-comum-layout.md) | Opção B do B04d: camada comum de layout (`LayoutItem`) entre conversores |
| [010](adr/010-reconhecimento-mineru.md) | Reconhecimento do MinerU Basic: campos reais, licença, custo — sem adaptador |
| [011](adr/011-ontologia-de-relacoes.md) | Ontologia de relações versionada; `claim_key` pelo RelationType; classe `alegada`; `narrative_scope` |
| [012](adr/012-gabarito-e-ancora.md) | Formato do gabarito e âncora de evidência (citação + contexto + posição) |

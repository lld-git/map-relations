# Mapa de arquivos .py

Atualizado em 2026-11-25, após o B02 (gabarito, avaliação e MLflow). Status possíveis:
**ativo** (no fluxo de execução), **só teste** (usado apenas por testes, em
geral contrato aguardando bloco futuro), **só script** (ferramenta de apoio),
**morto?** (candidato a remoção — conferir codigo_morto.txt).

| Arquivo | Papel | Quem importa | Status |
|---|---|---|---|
| research/map_relations/\_\_main\_\_.py | CLI: `python -m map_relations ingest <pdf>` | ninguém (ponto de entrada); tests/test_cli.py | ativo |
| research/map_relations/core/ids.py | UUIDs, NFC e chaves de conteúdo (claim_key lê a simetria do RelationType; asserted_by/narrative_scope na chave) | core/models, core/ingest_contract, ingest/document, ingest/canonical; testes | ativo |
| research/map_relations/core/models.py | 15 modelos Pydantic do domínio + enums | core/ingest_contract, core/rules, core/states, ingest/canonical, scripts/generate_schemas; testes | ativo |
| research/map_relations/core/ingest_contract.py | IngestResult, Paragraph, locate() | core/protocols, ingest/canonical, ingest/pdf_loader, ingest/report; testes | ativo |
| research/map_relations/core/protocols.py | Protocols: LlmEngine, SourceConnector, DocumentParser, ProjectStore, RunTracker (+ `check_local_tracking_uri`); erros do motor | tests/test_contracts, tests/test_ingest_contract | só teste (contrato para B03+) |
| research/map_relations/core/states.py | Tabela de transições do ADR 006 | core/rules; tests/test_states | ativo |
| research/map_relations/core/rules.py | validate_claim_kinds, new_claim (único caminho de criação de claim), transition com ChangeLog | tests/test_rules | só teste (entra no pipeline em B05/B07) |
| research/map_relations/core/ontology.py | modelos do YAML, build_ontology (junta todos os erros), canonicalize, ancestors/family, disjoint_conflicts, relation_types | core/rules, core/ontology_lock, ontology_io, scripts/generate_ontology; tests/test_ontology | ativo |
| research/map_relations/core/ontology_lock.py | trava de ids (relations.lock.json), sem I/O | scripts/generate_ontology; tests/test_ontology | ativo |
| research/map_relations/ontology_io.py | load_ontology: YAML seguro com rejeição de chave duplicada | \_\_main\_\_ (`ontology check`), scripts/generate_ontology; tests/test_ontology_io | ativo |
| research/map_relations/evaluation/gold.py | `GoldFile`, `Anchor`, `relation_proof`, `validate_gold` (regras do §3 que precisam de contexto) | evaluation/\*, scripts/generate_schemas; testes | ativo |
| research/map_relations/evaluation/anchoring.py | `resolve_anchor`: âncora por citação + contexto, nunca por offset antigo | evaluation/fill_offsets, evaluation/convert_draft; testes | ativo |
| research/map_relations/evaluation/fill_offsets.py | `gold fill-offsets`: tudo ou nada, relatório sem texto da obra | evaluation/gold_cli, evaluation/eval_cli; testes | ativo |
| research/map_relations/evaluation/convert_draft.py | `gold convert-draft`: conversão de uso único do rascunho | evaluation/gold_cli; testes | ativo |
| research/map_relations/evaluation/gold_cli.py | subcomandos `gold fill-offsets`, `convert-draft`, `validate` | \_\_main\_\_ | ativo |
| research/map_relations/evaluation/run_file.py | `RunFile`: formato da execução avaliada (B03 passa a emiti-lo) | evaluation/matching, evaluation/evaluate, eval_cli, scripts/generate_schemas; testes | ativo |
| research/map_relations/evaluation/matching.py | alinhamento por nome/alias, chaves estrita e relaxada, casamento exato e no tipo pai | evaluation/evaluate; testes | ativo |
| research/map_relations/evaluation/evaluate.py | métricas: tipo, família, atribuição, classe, nível/lente, prova, pessoas, controle, encaixado, alertas | evaluation/eval_cli; testes | ativo |
| research/map_relations/evaluation/report.py | métricas planas (nomes estáveis) e `report.md` | evaluation/eval_cli; testes | ativo |
| research/map_relations/evaluation/eval_cli.py | `eval --run --gold [--track]`; código 0 ou 2 | \_\_main\_\_; testes | ativo |
| research/map_relations/tracking/null_tracker.py | `NullTracker`, o `RunTracker` padrão | evaluation/eval_cli; testes | ativo |
| research/map_relations/tracking/mlflow_tracker.py | `MlflowTracker` (`mlflow-skinny`, import local; recusa endereço fora da máquina) | evaluation/eval_cli (só com `--track`); testes | ativo |
| research/map_relations/ingest/document.py | compute_text_hash; re-exporta Source | ingest/markdown, ingest/url_loader; tests/test_ingest | ativo |
| research/map_relations/ingest/markdown.py | convenção do .md, escape, render e parser único (ADR 008) | canonical, convert_*, \_\_main\_\_; tests/test_markdown | ativo |
| research/map_relations/ingest/layout.py | camada comum (ADR 009): LayoutItem/BBox, join_crossing_items, classify_titles, drop_page_furniture, compute_body_band/apply_body_band | canonical, convert_docling, convert_txt, docling_compare; tests/test_layout, test_layout_band | ativo |
| research/map_relations/ingest/canonical.py | rota pdf_loader: adaptador para a camada comum, precedência de títulos (classify_headings, não unificada — ver status.md), blocos | pdf_loader, convert_docling (despace/is_explicit_heading), convert_txt, convert_pandoc, docling_compare, \_\_main\_\_ | ativo |
| research/map_relations/ingest/convert_docling.py | docling.json → LayoutItem (DOCLING_LABEL_MAP) → MdBlocks; merge_range_docs/merged_layout_items juntam faixas e aplicam a faixa do corpo | \_\_main\_\_; tests/test_converters, test_docling_ranges, test_layout | ativo |
| research/map_relations/ingest/alerts.py | resolve alertas da conversão sobre o .md atual | report, \_\_main\_\_; tests/test_alerts | ativo |
| research/map_relations/ingest/convert_txt.py | TXT → MdBlocks | \_\_main\_\_; tests/test_converters | ativo |
| research/map_relations/ingest/convert_pandoc.py | EPUB/DOCX/HTML → MdBlocks via pandoc (experimental) | \_\_main\_\_; tests/test_converters | ativo |
| research/map_relations/ingest/store.py | layout processed/\<hash\>/, chave de cache Docling, órfãs | \_\_main\_\_; tests/test_store | ativo |
| research/map_relations/ingest/pdf_loader.py | extract_pages, load_pdf + PdfParser (DocumentParser) | \_\_main\_\_; tests/test_ingest_contract | ativo |
| research/map_relations/ingest/url_loader.py | load_url — ainda no formato antigo (Source, str) | ninguém | morto? (aguarda migração ao contrato no resto do B04) |
| research/map_relations/ingest/report.py | render_report e derivados em processed/\<hash\>/ | \_\_main\_\_; tests/test_ingest_contract | ativo |
| research/map_relations/ingest/docling_compare.py | relatório pdf_loader × conversor registrado, sobre LayoutItem[] (B04d fase 6; generalizado — era só Docling no B04b) | \_\_main\_\_ (CONVERTERS); tests/test_docling_compare | ativo |
| research/map_relations/nlp/ner.py | extract_mentions e unique_names com spaCy | tests/test_nlp | só teste (entra no pipeline em B05) |
| research/map_relations/\*/\_\_init\_\_.py (11 arquivos) | marcadores de pacote, vazios | — | ativo |
| scripts/generate_schemas.py | gera/verifica JSON Schemas em contracts/schemas | tests/test_contracts; CI (`--check`) | só script (e CI) |
| scripts/generate_ontology.py | gera/verifica relation-types.json, ontology.json, relations.lock.json e ontology-file.json | CI (`--check`), `make schema` | só script (e CI) |
| scripts/\_\_init\_\_.py | marcador de pacote | — | ativo |
| docs/mapa/vulture_whitelist.py | whitelist do vulture (não é código do projeto) | make map | só script |
| tests/test_cli.py | caminhos de erro da CLI | — | teste |
| tests/test_contracts.py | Protocols e coerência dos schemas | — | teste |
| tests/test_docling_compare.py | relatório de comparação (LayoutItem[]) com JSON sintético | — | teste |
| tests/test_markdown.py | parser único: convenção, escape, páginas, subtítulo | — | teste |
| tests/test_converters.py | conversores Docling/TXT/pandoc → MdBlocks | — | teste |
| tests/test_layout.py | camada comum: BBox, mapa de rótulos, join_crossing_items (E2), classify_titles, drop_page_furniture | — | teste |
| tests/test_layout_band.py | faixa do corpo: F1-F7 (compute_body_band/apply_body_band) | — | teste |
| tests/test_store.py | layout processed/, hash de arquivo, órfãs, cache por faixa | — | teste |
| tests/test_alerts.py | resolução de alertas da conversão sobre o .md atual | — | teste |
| tests/test_docling_ranges.py | junção de faixas, parágrafo cortado na fronteira | — | teste |
| tests/test_core_models.py | validadores, chaves, serialização camelCase | — | teste |
| tests/test_eval_runs.py | permissão de escrita em eval/runs (ADR 002) | — | teste |
| tests/test_ingest.py | Source e compute_text_hash | — | teste |
| tests/test_ingest_contract.py | B04: canônico, locate, relatório | — | teste |
| tests/test_nlp.py | NER com modelo pt (marker requires_spacy_model) | — | teste |
| tests/test_rules.py | kinds compatíveis, new_claim (abstrato, obsoleto, reflexivo), transition + ChangeLog | — | teste |
| tests/test_ontology.py | carregador, validação, canonicalize, conflitos, trava, geração | — | teste |
| tests/test_ontology_io.py | YAML: chave duplicada, arquivo real | — | teste |
| tests/test_states.py | todos os 5×5×2 pares de transição | — | teste |
| tests/eval_helpers.py | cenário sintético do `eval` (canônico, gabarito e execução inventados) | tests/test_eval, tests/test_tracking | teste |
| tests/test_eval.py | métricas esperadas à mão: estrita, relaxada, pai, atribuição, prova, controle, encaixado, CLI | — | teste |
| tests/test_tracking.py | `RunTracker`: endereços aceitos e recusados, nada da obra em params/tags, adaptador em `file://` | — | teste |
| tests/test_mlflow_config.py | porta 127.0.0.1:5010, versão fixa igual à do cliente, pastas ignoradas pelo Git | — | teste |

Cruzamento com codigo_morto.txt (vulture, confiança ≥ 60%): os itens
apontados são contratos/utilitários exercitados só em testes (locate,
transition, new_claim, is_terminal, docling_to_blocks, `furniture_hint` —
carregado para diagnóstico, nenhuma regra o lê, ver B.1 do plano B04d —,
PdfParser, write_processed, extract_mentions, unique_names, consultas de
`Ontology` como canonicalize/family/disjoint_conflicts, campos editoriais do
YAML da ontologia e os enums do escopo narrativo) — parte aguarda os blocos
B02–B07 — e `load_url` é o único candidato real a dívida (migração pendente ao
contrato de ingestão).

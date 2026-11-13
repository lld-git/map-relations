# Mapa de arquivos .py

Atualizado em 2026-11-12, após o B04c (Markdown intermediário). Status possíveis:
**ativo** (no fluxo de execução), **só teste** (usado apenas por testes, em
geral contrato aguardando bloco futuro), **só script** (ferramenta de apoio),
**morto?** (candidato a remoção — conferir codigo_morto.txt).

| Arquivo | Papel | Quem importa | Status |
|---|---|---|---|
| research/map_relations/\_\_main\_\_.py | CLI: `python -m map_relations ingest <pdf>` | ninguém (ponto de entrada); tests/test_cli.py | ativo |
| research/map_relations/core/ids.py | UUIDs, NFC e chaves de conteúdo (claim_key etc.) | core/models, core/ingest_contract, ingest/document, ingest/canonical; testes | ativo |
| research/map_relations/core/models.py | 15 modelos Pydantic do domínio + enums | core/ingest_contract, core/rules, core/states, ingest/canonical, scripts/generate_schemas; testes | ativo |
| research/map_relations/core/ingest_contract.py | IngestResult, Paragraph, locate() | core/protocols, ingest/canonical, ingest/pdf_loader, ingest/report; testes | ativo |
| research/map_relations/core/protocols.py | Protocols: LlmEngine, SourceConnector, DocumentParser, ProjectStore; erros do motor | tests/test_contracts, tests/test_ingest_contract | só teste (contrato para B03+) |
| research/map_relations/core/states.py | Tabela de transições do ADR 006 | core/rules; tests/test_states | ativo |
| research/map_relations/core/rules.py | validate_claim_kinds, transition com ChangeLog | tests/test_rules | só teste (entra no pipeline em B05/B07) |
| research/map_relations/ingest/document.py | compute_text_hash; re-exporta Source | ingest/markdown, ingest/url_loader; tests/test_ingest | ativo |
| research/map_relations/ingest/markdown.py | convenção do .md, escape, render e parser único (ADR 008) | canonical, convert_*, \_\_main\_\_; tests/test_markdown | ativo |
| research/map_relations/ingest/canonical.py | rota pdf_loader: limpeza de páginas, precedência de títulos, blocos | pdf_loader, convert_docling, convert_txt, convert_pandoc, \_\_main\_\_ | ativo |
| research/map_relations/ingest/convert_docling.py | docling.json → MdBlocks; merge_range_docs junta faixas na fronteira | \_\_main\_\_; tests/test_converters, test_docling_ranges | ativo |
| research/map_relations/ingest/alerts.py | resolve alertas da conversão sobre o .md atual | report, \_\_main\_\_; tests/test_alerts | ativo |
| research/map_relations/ingest/convert_txt.py | TXT → MdBlocks | \_\_main\_\_; tests/test_converters | ativo |
| research/map_relations/ingest/convert_pandoc.py | EPUB/DOCX/HTML → MdBlocks via pandoc (experimental) | \_\_main\_\_; tests/test_converters | ativo |
| research/map_relations/ingest/store.py | layout processed/\<hash\>/, chave de cache Docling, órfãs | \_\_main\_\_; tests/test_store | ativo |
| research/map_relations/ingest/pdf_loader.py | extract_pages, load_pdf + PdfParser (DocumentParser) | \_\_main\_\_; tests/test_ingest_contract | ativo |
| research/map_relations/ingest/url_loader.py | load_url — ainda no formato antigo (Source, str) | ninguém | morto? (aguarda migração ao contrato no resto do B04) |
| research/map_relations/ingest/report.py | render_report e derivados em processed/\<hash\>/ | \_\_main\_\_; tests/test_ingest_contract | ativo |
| research/map_relations/ingest/docling_compare.py | relatório pdf_loader × Docling (prova B04b) | \_\_main\_\_; tests/test_docling_compare | ativo |
| research/map_relations/nlp/ner.py | extract_mentions e unique_names com spaCy | tests/test_nlp | só teste (entra no pipeline em B05) |
| research/map_relations/\*/\_\_init\_\_.py (11 arquivos) | marcadores de pacote, vazios | — | ativo |
| scripts/generate_schemas.py | gera/verifica JSON Schemas em contracts/schemas | tests/test_contracts; CI (`--check`) | só script (e CI) |
| scripts/\_\_init\_\_.py | marcador de pacote | — | ativo |
| docs/mapa/vulture_whitelist.py | whitelist do vulture (não é código do projeto) | make map | só script |
| tests/test_cli.py | caminhos de erro da CLI | — | teste |
| tests/test_contracts.py | Protocols e coerência dos schemas | — | teste |
| tests/test_docling_compare.py | relatório de comparação com JSON sintético | — | teste |
| tests/test_markdown.py | parser único: convenção, escape, páginas, subtítulo | — | teste |
| tests/test_converters.py | conversores Docling/TXT/pandoc → MdBlocks | — | teste |
| tests/test_store.py | layout processed/, hash de arquivo, órfãs, cache por faixa | — | teste |
| tests/test_alerts.py | resolução de alertas da conversão sobre o .md atual | — | teste |
| tests/test_docling_ranges.py | junção de faixas, parágrafo cortado na fronteira | — | teste |
| tests/test_core_models.py | validadores, chaves, serialização camelCase | — | teste |
| tests/test_eval_runs.py | permissão de escrita em eval/runs (ADR 002) | — | teste |
| tests/test_ingest.py | Source e compute_text_hash | — | teste |
| tests/test_ingest_contract.py | B04: canônico, locate, relatório | — | teste |
| tests/test_nlp.py | NER com modelo pt (marker requires_spacy_model) | — | teste |
| tests/test_rules.py | kinds compatíveis, transition + ChangeLog | — | teste |
| tests/test_states.py | todos os 5×5×2 pares de transição | — | teste |

Cruzamento com codigo_morto.txt (vulture, confiança ≥ 60%): dos 11 itens
apontados, 10 são contratos/utilitários exercitados só em testes (locate,
validate_claim_kinds, transition, is_terminal, docling_to_blocks,
docling_range, PdfParser, write_processed, extract_mentions, unique_names) —
parte aguarda os blocos B02–B07 — e `load_url` é o único candidato real a
dívida (migração pendente ao contrato de ingestão).

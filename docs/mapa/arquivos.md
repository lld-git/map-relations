# Mapa de arquivos .py

Atualizado em 2026-11-11, após o B04 antecipado. Status possíveis:
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
| research/map_relations/ingest/document.py | compute_text_hash; re-exporta Source | ingest/canonical, ingest/url_loader; tests/test_ingest | ativo |
| research/map_relations/ingest/canonical.py | build_ingest_result: texto canônico, parágrafos, capítulos, removidos | ingest/pdf_loader; tests/test_ingest_contract | ativo |
| research/map_relations/ingest/pdf_loader.py | load_pdf + PdfParser (DocumentParser) | \_\_main\_\_; tests/test_ingest_contract | ativo |
| research/map_relations/ingest/url_loader.py | load_url — ainda no formato antigo (Source, str) | ninguém | morto? (aguarda migração ao contrato no resto do B04) |
| research/map_relations/ingest/report.py | write_processed: data/processed/\<hash\>/ | \_\_main\_\_; tests/test_ingest_contract | ativo |
| research/map_relations/nlp/ner.py | extract_mentions e unique_names com spaCy | tests/test_nlp | só teste (entra no pipeline em B05) |
| research/map_relations/\*/\_\_init\_\_.py (11 arquivos) | marcadores de pacote, vazios | — | ativo |
| scripts/generate_schemas.py | gera/verifica JSON Schemas em contracts/schemas | tests/test_contracts; CI (`--check`) | só script (e CI) |
| scripts/\_\_init\_\_.py | marcador de pacote | — | ativo |
| docs/mapa/vulture_whitelist.py | whitelist do vulture (não é código do projeto) | make map | só script |
| tests/test_cli.py | caminhos de erro da CLI | — | teste |
| tests/test_contracts.py | Protocols e coerência dos schemas | — | teste |
| tests/test_core_models.py | validadores, chaves, serialização camelCase | — | teste |
| tests/test_eval_runs.py | permissão de escrita em eval/runs (ADR 002) | — | teste |
| tests/test_ingest.py | Source e compute_text_hash | — | teste |
| tests/test_ingest_contract.py | B04: canônico, locate, relatório | — | teste |
| tests/test_nlp.py | NER com modelo pt (marker requires_spacy_model) | — | teste |
| tests/test_rules.py | kinds compatíveis, transition + ChangeLog | — | teste |
| tests/test_states.py | todos os 5×5×2 pares de transição | — | teste |

Cruzamento com codigo_morto.txt (vulture, confiança ≥ 60%): os 8 itens
apontados são funções de contrato usadas só em testes (locate,
validate_claim_kinds, transition, is_terminal, PdfParser, extract_mentions,
unique_names) — aguardam os blocos B02–B07 — e `load_url`, o único candidato
real a dívida (migração pendente ao contrato de ingestão).

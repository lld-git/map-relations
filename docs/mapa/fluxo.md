# Fluxo de dados — único diagrama de fluxo do projeto

Atualizado em 2026-11-12, após o B04c (Markdown intermediário, ADR 008).
Linhas cheias = confirmado no código (cada seta cita arquivo.py:função).
Tracejado = planejado.

```mermaid
flowchart TB
    RAW["arquivo em data/raw/<br/>(PDF, TXT, EPUB, DOCX, HTML)"]
    CLI["__main__.py:cmd_ingest"]
    CACHE["cache por faixa<br/>processed/&lt;hash&gt;/docling/&lt;versão&gt;-&lt;opções&gt;/pages_XXXX-YYYY.json"]
    CONVD["convert_docling.py:merge_range_docs<br/>(junta faixas + regra de fronteira)"]
    CONVP["canonical.py:pdf_pages_to_blocks<br/>(rota pdf_loader)"]
    CONVT["convert_txt.py:txt_to_blocks"]
    CONVPD["convert_pandoc.py:convert_pandoc"]
    MD["documento.md (FONTE)<br/>+ conversao.json"]
    HUMANO["revisão humana<br/>(edita o .md)"]
    PARSER["markdown.py:parse_markdown<br/>(parser único)"]
    RESULT["IngestResult<br/>(core/ingest_contract.py)"]
    OUT["canonical.txt + ingest.json + report.md"]
    COMPARE["comparacao_docling.md"]

    RAW -->|"Makefile:docling → docling convert por faixa (processo separado)"| CACHE
    RAW -->|"__main__.py:_resolve_raw + store.py:file_hash"| CLI
    CACHE -->|"__main__.py:_generate_md (lê todas as faixas)"| CONVD
    CLI -->|"--route pdf_loader: pdf_loader.py:extract_pages"| CONVP
    CLI -->|".txt"| CONVT
    CLI -->|".epub/.docx/.html via pandoc"| CONVPD
    CONVD -->|"markdown.py:render_markdown (escape + <!-- p.N -->)"| MD
    CONVP -->|"markdown.py:render_markdown"| MD
    CONVT -->|"markdown.py:render_markdown"| MD
    CONVPD -->|"markdown.py:render_markdown"| MD
    MD <-->|"nunca sobrescrita sem --force-md"| HUMANO
    MD -->|"__main__.py:_parse_existing"| PARSER
    PARSER --> RESULT
    RESULT -->|"__main__.py:cmd_ingest + report.py:render_report"| OUT
    CACHE -->|"__main__.py:cmd_compare → docling_compare.py:compare"| COMPARE

    SEG["segmentação + N0/N1 (B05)"]
    EVAL["eval contra gabarito (B02)"]
    RESULT -.->|"planejado: pipeline spaCy + regras (B05)"| SEG
    RESULT -.->|"planejado: offsets do gabarito usam o texto canônico (B02)"| EVAL
```

Notas confirmadas no código:

- Rota padrão de PDF é o Docling via cache (`store.py:DOCLING_CACHE_KEY` =
  versão + opções); sem cache a CLI sai com código 3 e o Makefile roda o
  serviço e repete (`Makefile:ingest`).
- `documento.md` é a fonte revisada: se existe, a ingestão o reaproveita e
  nunca o regenera sem `--force-md` (`__main__.py:cmd_ingest`).
- Editar o .md muda o hash canônico e invalida offsets de gabarito/evidências
  (regra do ADR 008; teste `test_human_edit_changes_canonical_hash`).
- Marcadores `<!-- p.N -->` dão a página de cada parágrafo e não entram no
  canônico (`markdown.py:_parse_blocks`).
- `url_loader.py:load_url` segue fora do fluxo (pendência do B04).
- `make clean-processed` lista pastas órfãs; só remove com `APPLY=1`
  (`store.py:orphans` não apaga nada).

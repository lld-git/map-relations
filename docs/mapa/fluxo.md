# Fluxo de dados — único diagrama de fluxo do projeto

Atualizado em 2026-11-12, após a prova do Docling (B04b-prova). Linhas cheias =
confirmado no código (cada seta cita arquivo.py:função). Tracejado = planejado.

```mermaid
flowchart TB
    PDF["PDF em data/raw/"]
    CLI["__main__.py:cmd_ingest"]
    LOAD["pdf_loader.py:load_pdf"]
    BUILD["canonical.py:build_ingest_result"]
    RESULT["IngestResult<br/>(core/ingest_contract.py)"]
    OUT["data/processed/&lt;hash&gt;/<br/>canonical.txt + ingest.json + report.md"]

    PDF -->|"__main__.py:cmd_ingest valida data/raw/"| CLI
    CLI -->|"__main__.py:cmd_ingest → pdf_loader.py:load_pdf"| LOAD
    LOAD -->|"pdf_loader.py:load_pdf → canonical.py:build_ingest_result"| BUILD
    BUILD -->|"canonical.py:_clean_pages, _join_pages, _split_paragraph_blocks; ids.py:nfc; document.py:compute_text_hash"| RESULT
    RESULT -->|"__main__.py:cmd_ingest → report.py:write_processed"| OUT

    DOCJSON["data/docling/&lt;nome&gt;.json"]
    COMPARE["comparacao_docling.md<br/>em data/processed/&lt;hash&gt;/"]

    PDF -->|"make docling (serviço docling, CLI docling --to json)"| DOCJSON
    DOCJSON -->|"__main__.py:cmd_compare → docling_compare.py:compare"| COMPARE
    RESULT -->|"__main__.py:cmd_compare"| COMPARE

    URL["URL / TXT / EPUB"]
    DOCLINGPARSER["DoclingParser (B04b)"]
    SEG["segmentação + N0/N1 (B05)"]
    EVAL["eval contra gabarito (B02)"]

    URL -.->|"planejado: migrar url_loader.py:load_url ao contrato; TXT/EPUB no resto do B04"| BUILD
    DOCJSON -.->|"planejado: DoclingParser → IngestResult (B04b)"| DOCLINGPARSER
    DOCLINGPARSER -.->|"planejado"| RESULT
    RESULT -.->|"planejado: pipeline spaCy + regras (B05)"| SEG
    RESULT -.->|"planejado: offsets do gabarito usam o texto canônico (B02)"| EVAL
```

Notas confirmadas no código:

- A validação "PDF deve estar em data/raw/" e os códigos de saída estão em
  `__main__.py:cmd_ingest` (0 sucesso, 2 entrada inválida, 1 falha de processamento).
- `canonical.py:build_ingest_result` cria o `Source` com
  `document.py:compute_text_hash` sobre o texto canônico NFC, e monta
  parágrafos e capítulos com offsets em code points (ADR 004).
- `ingest_contract.py:locate` converte offset em "cap. X, § Y"; é referência
  legível, nunca usada para verificar provas.
- `url_loader.py:load_url` existe mas ainda retorna `(Source, str)` — não está
  ligado ao fluxo (por isso tracejado).

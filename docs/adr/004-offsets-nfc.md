# ADR 004 — Offsets em Unicode code points sobre texto NFC

**Data:** 2026-11-10  
**Status:** aceito

## Contexto

Mention, Segment e Evidence carregam `start_offset`/`end_offset` que precisam
reconstruir exatamente o trecho citado (`quote`) a partir do texto da fonte —
inclusive após o porte para TypeScript. Offsets em bytes variam por encoding;
offsets em unidades UTF-16 (padrão de JavaScript) divergem do `len()` de
Python em caracteres fora do BMP; composição Unicode (é = 1 ou 2 code points)
muda contagens entre extratores.

## Decisão

1. Todo texto é normalizado para **NFC** (`unicodedata.normalize("NFC", ...)`)
   na ingestão, antes de qualquer segmentação ou extração (`core/ids.py: nfc`).
2. Offsets contam **Unicode code points** sobre esse texto NFC — o que
   `str[i:j]` retorna em Python. Nunca bytes, nunca unidades UTF-16.
3. `source.content_hash` é sha256 do texto NFC em UTF-8
   (`ingest/document.py: compute_text_hash`). Hash e offsets referenciam a
   mesma representação.
4. Validação em código: `start_offset >= 0` e `start_offset < end_offset`
   em todos os modelos com offsets.

## Consequências

- Invariante testável: `texto_nfc[start:end] == quote`.
- O porte TypeScript deve converter code points ↔ unidades UTF-16
  (`String.prototype.codePointAt` / iteração por code points), nunca usar
  índices de string JS diretamente.
- Qualquer parser novo (Docling em B04b) deve passar pelo mesmo `nfc()`
  antes de emitir offsets.

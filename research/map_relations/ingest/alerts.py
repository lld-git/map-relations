"""Resolução de alertas da conversão sobre o documento.md atual (ADR 008).

Os alertas dividem-se em dois grupos:
- os do parser (markdown.parse_markdown) são calculados sempre sobre o .md
  atual — vão em IngestResult.quality.alerts;
- os da conversão (classify_headings, docling_to_blocks) são gravados em
  conversao.json no momento da conversão. Aqui marcamos cada um como resolvido
  quando o .md editado não o reproduz mais.

Houve edição quando o hash do .md atual difere do hash gravado em conversao.json
(markdown.md_hash). Sem edição, nenhum alerta da conversão é resolvido.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from map_relations.core.ingest_contract import ParagraphKind

from .canonical import is_explicit_heading
from .markdown import parse_blocks

# alertas de detalhe citam o trecho entre aspas no fim da mensagem
_SNIPPET_RE = re.compile(r': "(.+?)"$')


@dataclass
class ConversionAlert:
    message: str
    resolved: bool


def _reproduced(alert: str, plain_texts: list[str], has_explicit_chapter: bool) -> bool:
    """O .md atual ainda reproduz a condição descrita pelo alerta?"""
    snippet = _SNIPPET_RE.search(alert)
    if snippet:
        # detalhe: reproduzido enquanto o trecho seguir como parágrafo de texto
        needle = snippet.group(1).rstrip("…").strip()
        return any(needle in t for t in plain_texts)
    if "confirmar na revisão" in alert:
        # resumo "capítulos só por maiúsculas/layout": resolvido quando a
        # revisão estabelece ao menos um capítulo explícito
        return not has_explicit_chapter
    return True  # alerta desconhecido: mantém, conservador


def classify_conversion_alerts(
    conversion_alerts: list[str], current_md: str, edited: bool
) -> list[ConversionAlert]:
    if not edited:
        return [ConversionAlert(a, resolved=False) for a in conversion_alerts]
    blocks = parse_blocks(current_md)
    plain_texts = [b.text for b in blocks if b.kind is ParagraphKind.texto]
    has_explicit_chapter = any(
        b.kind is ParagraphKind.titulo and is_explicit_heading(b.text) for b in blocks
    )
    return [
        ConversionAlert(a, resolved=not _reproduced(a, plain_texts, has_explicit_chapter))
        for a in conversion_alerts
    ]

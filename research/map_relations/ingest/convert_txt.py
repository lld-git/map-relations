"""Conversor TXT: texto puro → blocos do Markdown intermediário.

Sem páginas. Parágrafos separados por linha em branco; títulos pela mesma
precedência genérica das outras rotas.
"""

from __future__ import annotations

import re

from map_relations.core.ingest_contract import ParagraphKind, RemovedItem

from .canonical import classify_headings
from .markdown import MdBlock


def txt_to_blocks(text: str) -> tuple[list[MdBlock], list[RemovedItem], list[str]]:
    paragraphs = [
        re.sub(r"\s+", " ", block).strip()
        for block in re.split(r"\n\s*\n", text)
        if block.strip()
    ]
    is_heading, alerts = classify_headings(paragraphs)
    blocks = [
        MdBlock(p, ParagraphKind.titulo if h else ParagraphKind.texto)
        for p, h in zip(paragraphs, is_heading)
    ]
    return blocks, [], alerts

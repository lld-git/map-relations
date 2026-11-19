"""Conversor TXT: texto puro → blocos do Markdown intermediário.

Sem páginas. Parágrafos separados por linha em branco; títulos pela mesma
precedência genérica das outras rotas.

B04d fase 4: adaptador sem `page` nem `bbox` para a camada comum — vira
LayoutItem numa só faixa (sem fronteira entre páginas para
join_crossing_items juntar) e usa canonical.layout_items_to_blocks, em vez de
chamar classify_headings direto.
"""

from __future__ import annotations

import re

from map_relations.core.ingest_contract import RemovedItem

from .canonical import layout_items_to_blocks
from .layout import LayoutItem, LayoutLabel
from .markdown import MdBlock


def txt_to_blocks(text: str) -> tuple[list[MdBlock], list[RemovedItem], list[str]]:
    paragraphs = [
        re.sub(r"\s+", " ", block).strip()
        for block in re.split(r"\n\s*\n", text)
        if block.strip()
    ]
    items = [
        LayoutItem(
            order=i, label=LayoutLabel.texto, text=p, source_label="paragraph", converter="txt"
        )
        for i, p in enumerate(paragraphs)
    ]
    blocks, alerts = layout_items_to_blocks([items])
    return blocks, [], alerts

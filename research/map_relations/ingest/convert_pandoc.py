"""Conversor pandoc: EPUB, DOCX e HTML → blocos do Markdown intermediário.

Experimental (ADR 008): o pandoc gera CommonMark; daqui tiramos só o
subconjunto da convenção — linhas de título (#) e parágrafos. Escapes do
próprio pandoc são removidos para o texto voltar literal.

B04d fase 4: adaptador sem `page` nem `bbox` para a camada comum — vira
LayoutItem numa só faixa e usa canonical.layout_items_to_blocks para a
precedência de títulos explícitos; o título nativo do pandoc (`#`) é um
sinal à parte, sempre título, aplicado depois (OR, não entra na
precedência de classify_headings)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from map_relations.core.ingest_contract import ParagraphKind, RemovedItem

from .canonical import layout_items_to_blocks
from .layout import LayoutItem, LayoutLabel
from .markdown import MdBlock

_PANDOC_ESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!<>\"'~])")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def run_pandoc(path: Path) -> str:
    out = subprocess.run(
        ["pandoc", str(path), "--to", "commonmark", "--wrap", "none"],
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def pandoc_md_to_blocks(
    md: str,
) -> tuple[list[MdBlock], list[RemovedItem], list[str]]:
    paragraphs: list[tuple[str, bool]] = []  # (texto, é_heading_pandoc)
    for block in re.split(r"\n\s*\n", md):
        block = block.strip()
        if not block:
            continue
        m = _HEADING_RE.match(block.splitlines()[0])
        if m and len(block.splitlines()) == 1:
            paragraphs.append((_PANDOC_ESCAPE_RE.sub(r"\1", m.group(2).strip()), True))
        else:
            flat = re.sub(r"\s+", " ", _PANDOC_ESCAPE_RE.sub(r"\1", block)).strip()
            if flat:
                paragraphs.append((flat, False))

    items = [
        LayoutItem(
            order=i, label=LayoutLabel.texto, text=t, source_label="paragraph", converter="pandoc"
        )
        for i, (t, _) in enumerate(paragraphs)
    ]
    blocks, alerts = layout_items_to_blocks([items])
    for block, (_, pandoc_heading) in zip(blocks, paragraphs):
        if pandoc_heading:
            block.kind = ParagraphKind.titulo
    return blocks, [], alerts


def convert_pandoc(path: Path) -> tuple[list[MdBlock], list[RemovedItem], list[str]]:
    return pandoc_md_to_blocks(run_pandoc(path))

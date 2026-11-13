"""Conversor pandoc: EPUB, DOCX e HTML → blocos do Markdown intermediário.

Experimental (ADR 008): o pandoc gera CommonMark; daqui tiramos só o
subconjunto da convenção — linhas de título (#) e parágrafos. Escapes do
próprio pandoc são removidos para o texto voltar literal.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from map_relations.core.ingest_contract import ParagraphKind, RemovedItem

from .canonical import classify_headings
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

    texts = [t for t, _ in paragraphs]
    explicit_heading, alerts = classify_headings(texts)
    blocks: list[MdBlock] = []
    for (text, pandoc_heading), explicit in zip(paragraphs, explicit_heading):
        kind = (
            ParagraphKind.titulo
            if explicit or pandoc_heading
            else ParagraphKind.texto
        )
        blocks.append(MdBlock(text, kind))
    return blocks, [], alerts


def convert_pandoc(path: Path) -> tuple[list[MdBlock], list[RemovedItem], list[str]]:
    return pandoc_md_to_blocks(run_pandoc(path))

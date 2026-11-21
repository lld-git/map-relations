"""Markdown estruturado — formato intermediário único da ingestão (ADR 008).

Convenção (subconjunto restrito; todo o resto é texto literal):
- "# Título"                        → título de capítulo (um # só)
- linha inteira "*...*" logo após o título → subtítulo
- parágrafos separados por linha em branco
- "<!-- p.N -->" em linha própria   → marcador de página (não entra no canônico)

O parser NÃO interpreta Markdown completo: texto de documento é dado, nunca
instrução (Princípio 8). Os conversores escapam os caracteres que colidem com
a convenção; o parser des-escapa ao montar o texto canônico.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass

from map_relations.core.ids import nfc
from map_relations.core.ingest_contract import (
    ChapterSpan,
    IngestResult,
    Paragraph,
    ParagraphKind,
    QualityReport,
    RemovedItem,
)
from map_relations.core.models import Source

from .document import compute_text_hash

_PAGE_MARKER_RE = re.compile(r"^<!--\s*p\.(\d+)\s*-->$")
# ordem importa: barra primeiro no escape, por último no unescape
_ESCAPES = [("\\", "\\\\"), ("#", "\\#"), ("*", "\\*"), ("<!--", "<\\!--")]

# travessão/hífen de fala no início de uma linha de parágrafo: escapado com
# "\" só aí (nunca no meio da linha), para editores Markdown não lerem como
# item de lista. O canônico nunca vê essa barra — é des-escapada ao ler.
_LEADING_DASHES = ("-", "–", "—", "―")


@dataclass
class MdBlock:
    """Bloco lógico produzido pelos conversores, antes da serialização."""

    text: str
    kind: ParagraphKind = ParagraphKind.texto
    page: int | None = None


def md_hash(md: str) -> str:
    """sha256 do documento.md literal — detecta edição humana (ADR 008).

    Distinto do content_hash (sha256 do texto canônico NFC): este compara o
    arquivo editável, aquele o derivado sem marcação."""
    return hashlib.sha256(md.encode("utf-8")).hexdigest()


def escape_md(text: str) -> str:
    for plain, escaped in _ESCAPES:
        text = text.replace(plain, escaped)
    return text


def unescape_md(text: str) -> str:
    for plain, escaped in reversed(_ESCAPES):
        text = text.replace(escaped, plain)
    return text


def render_markdown(blocks: list[MdBlock]) -> str:
    """Serializa blocos no Markdown da convenção, com marcadores de página."""
    out: list[str] = []
    current_page: int | None = None
    for block in blocks:
        if block.page is not None and block.page != current_page:
            out.append(f"<!-- p.{block.page} -->")
            current_page = block.page
        text = escape_md(block.text)
        if block.kind is ParagraphKind.titulo:
            out.append(f"# {text}")
        elif block.kind is ParagraphKind.subtitulo:
            out.append(f"*{text}*")
        else:
            if text.startswith(_LEADING_DASHES):
                text = "\\" + text
            out.append(text)
    return "\n\n".join(out) + ("\n" if out else "")


def parse_blocks(md: str) -> list[MdBlock]:
    """Lê o Markdown da convenção de volta para blocos lógicos."""
    blocks: list[MdBlock] = []
    page: int | None = None
    previous_was_title = False
    for raw in re.split(r"\n\s*\n", md):
        line = raw.strip()
        if not line:
            continue
        marker = _PAGE_MARKER_RE.match(line)
        if marker:
            page = int(marker.group(1))
            continue
        if line.startswith("# "):
            blocks.append(
                MdBlock(unescape_md(line[2:].strip()), ParagraphKind.titulo, page)
            )
            previous_was_title = True
            continue
        if (
            previous_was_title
            and len(line) > 2
            and line.startswith("*")
            and line.endswith("*")
            and "*" not in line[1:-1]
        ):
            blocks.append(
                MdBlock(unescape_md(line[1:-1].strip()), ParagraphKind.subtitulo, page)
            )
            previous_was_title = False
            continue
        previous_was_title = False
        if len(line) > 1 and line[0] == "\\" and line[1] in _LEADING_DASHES:
            line = line[1:]
        # parágrafo: quebras internas viram espaço (canônico é uma linha por bloco)
        flat = re.sub(r"\s+", " ", unescape_md(line)).strip()
        if flat:
            blocks.append(MdBlock(flat, ParagraphKind.texto, page))
    return blocks


def parse_markdown(
    md: str,
    title: str,
    kind: str,
    *,
    removed: list[RemovedItem] | None = None,
    extra_alerts: list[str] | None = None,
    pages: int = 0,
) -> IngestResult:
    """Parser único: documento.md → IngestResult (texto canônico NFC,
    parágrafos com página, capítulos, subtítulos, QualityReport)."""
    removed = removed or []
    alerts = list(extra_alerts or [])
    blocks = parse_blocks(md)
    for b in blocks:
        b.text = nfc(b.text)

    text = "\n\n".join(b.text for b in blocks)
    source = Source(title=title, kind=kind, content_hash=compute_text_hash(text))

    paragraphs: list[Paragraph] = []
    chapters: list[ChapterSpan] = []
    offset = 0
    chapter: int | None = None
    number_in_chapter = 0

    for i, block in enumerate(blocks):
        if i > 0:
            offset += 2  # separador "\n\n"
        start, end = offset, offset + len(block.text)
        if block.kind is ParagraphKind.titulo:
            if chapters:
                chapters[-1] = chapters[-1].model_copy(update={"end_offset": start})
            chapter = len(chapters) + 1
            chapters.append(
                ChapterSpan(
                    index=chapter, title=block.text, start_offset=start, end_offset=end
                )
            )
            number_in_chapter = 0
            number = 0
        elif block.kind is ParagraphKind.subtitulo:
            number = 0
        else:
            number_in_chapter += 1
            number = number_in_chapter
        paragraphs.append(
            Paragraph(
                source_id=source.id,
                chapter=chapter,
                number=number,
                kind=block.kind,
                page=block.page,
                start_offset=start,
                end_offset=end,
            )
        )
        offset = end

    if chapters:
        chapters[-1] = chapters[-1].model_copy(update={"end_offset": len(text)})
    else:
        alerts.append("nenhum capítulo detectado")
    if not text:
        alerts.append("texto canônico vazio")

    texto_por_capitulo = Counter(
        p.chapter for p in paragraphs if p.kind is ParagraphKind.texto
    )
    for ch in chapters:
        if texto_por_capitulo.get(ch.index, 0) == 0:
            alerts.append(f"capítulo {ch.index} sem parágrafos de texto")

    last_page = max((b.page for b in blocks if b.page), default=0)
    quality = QualityReport(
        pages=pages or last_page,
        chapters_detected=len(chapters),
        paragraphs=len(paragraphs),
        removed_by_reason=dict(Counter(item.reason.value for item in removed)),
        alerts=alerts,
    )
    return IngestResult(
        source=source,
        text=text,
        paragraphs=paragraphs,
        chapters=chapters,
        removed=removed,
        quality=quality,
    )

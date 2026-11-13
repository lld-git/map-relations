"""Monta o IngestResult a partir das páginas brutas de um parser.

Separado do pdf_loader para ser testável com páginas sintéticas e
reutilizável por TXT/EPUB (resto do B04) e DoclingParser (B04b).
"""

from __future__ import annotations

import re
from collections import Counter

from map_relations.core.ids import nfc
from map_relations.core.ingest_contract import (
    ChapterSpan,
    IngestResult,
    Paragraph,
    ParagraphKind,
    QualityReport,
    RemovalReason,
    RemovedItem,
)
from map_relations.core.models import Source

from .document import compute_text_hash

# Linha repetida no início/fim de pelo menos esta fração das páginas é
# tratada como cabeçalho/rodapé.
_REPEAT_THRESHOLD = 0.6

_PAGE_NUMBER_RE = re.compile(r"^[\s\-–—]*\d{1,4}[\s\-–—]*$")

# Padrões explícitos de capítulo (com e sem espaçamento entre letras).
_CHAPTER_RES = [
    re.compile(r"^cap[íi]tulo\s+\S+", re.IGNORECASE),
    re.compile(r"^[IVXLCDM]{1,7}\.?$"),
]
# Versões sobre o texto sem espaços ("C A P Í T U L O I" → "capítuloi").
_CHAPTER_DESPACED_RES = [
    re.compile(r"^cap[íi]tulo", re.IGNORECASE),
    re.compile(r"^[IVXLCDM]{1,7}\.?$", re.IGNORECASE),
]


def _despace(line: str) -> str:
    """Remove espaçamento tipográfico entre letras, para detecção apenas.
    Só age quando a maioria dos tokens é de um caractere (letras espaçadas)."""
    tokens = line.split()
    if len(tokens) >= 4 and sum(len(t) == 1 for t in tokens) / len(tokens) >= 0.7:
        return "".join(tokens)
    return line


def _is_explicit_heading(line: str) -> bool:
    """Título que casa um padrão explícito de capítulo (Capítulo N, romanos),
    inclusive com letras espaçadas."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if any(rx.match(line) for rx in _CHAPTER_RES):
        return True
    despaced = _despace(line)
    return despaced != line and any(rx.match(despaced) for rx in _CHAPTER_DESPACED_RES)


def _is_uppercase_heading(line: str) -> bool:
    """Linha curta toda em maiúsculas — candidata a título, menos confiável."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(line) >= 3


def _is_chapter_heading(line: str) -> bool:
    return _is_explicit_heading(line) or _is_uppercase_heading(line)


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _find_repeated_edges(pages: list[list[str]]) -> tuple[set[str], set[str]]:
    """Linhas (normalizadas) que se repetem no topo/rodapé das páginas."""
    nonempty = [p for p in pages if p]
    if len(nonempty) < 3:
        return set(), set()
    threshold = max(2, int(len(nonempty) * _REPEAT_THRESHOLD))
    tops = Counter(_normalize_line(p[0]) for p in nonempty)
    bottoms = Counter(_normalize_line(p[-1]) for p in nonempty)
    headers = {line for line, n in tops.items() if n >= threshold and line}
    footers = {line for line, n in bottoms.items() if n >= threshold and line}
    return headers, footers


def _clean_pages(
    raw_pages: list[str],
) -> tuple[list[str], list[RemovedItem], list[str]]:
    """Remove cabeçalhos, rodapés e números de página das bordas de cada
    página, preservando linhas em branco (estrutura de parágrafos)."""
    pages_lines = [page.splitlines() for page in raw_pages]
    content_lines = [[ln for ln in lines if ln.strip()] for lines in pages_lines]
    headers, footers = _find_repeated_edges(content_lines)
    removed: list[RemovedItem] = []
    alerts: list[str] = []
    cleaned: list[str] = []

    for page_no, (lines, content) in enumerate(
        zip(pages_lines, content_lines), start=1
    ):
        if not content:
            removed.append(
                RemovedItem(page=page_no, reason=RemovalReason.pagina_vazia, text="")
            )
            alerts.append(f"página {page_no} sem texto")
            cleaned.append("")
            continue
        idxs = [i for i, ln in enumerate(lines) if ln.strip()]
        first, last = idxs[0], idxs[-1]
        drop: set[int] = set()
        norm_first = _normalize_line(lines[first])
        norm_last = _normalize_line(lines[last])
        if norm_first in headers:
            drop.add(first)
            removed.append(
                RemovedItem(page=page_no, reason=RemovalReason.cabecalho, text=norm_first)
            )
        if last != first and norm_last in footers:
            drop.add(last)
            removed.append(
                RemovedItem(page=page_no, reason=RemovalReason.rodape, text=norm_last)
            )
        for i in dict.fromkeys((first, last)):  # dedupe preservando ordem
            norm = _normalize_line(lines[i])
            if i not in drop and _PAGE_NUMBER_RE.match(norm):
                drop.add(i)
                removed.append(
                    RemovedItem(
                        page=page_no, reason=RemovalReason.numero_pagina, text=norm
                    )
                )
        kept = [ln for i, ln in enumerate(lines) if i not in drop]
        cleaned.append("\n".join(kept).strip("\n"))
    return cleaned, removed, alerts


def _join_pages(pages: list[str]) -> str:
    """Une páginas corrigindo palavras hifenizadas na quebra de página."""
    out = ""
    for page in pages:
        if not page:
            continue
        if out.endswith("-"):
            out = out[:-1] + page.lstrip()  # palavra atravessa a página
        elif out:
            out += "\n\n" + page
        else:
            out = page
    return out


def _split_paragraph_blocks(text: str) -> list[str]:
    text = re.sub(r"-\n", "", text)         # junta palavras hifenizadas
    text = re.sub(r"[^\S\n]+", " ", text)   # colapsa espaços, preserva \n
    # títulos de capítulo viram blocos próprios mesmo sem linha em branco
    isolated: list[str] = []
    for line in text.split("\n"):
        if _is_chapter_heading(line):
            isolated.extend(["", line.strip(), ""])
        else:
            isolated.append(line)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(isolated))
    blocks = []
    for block in text.split("\n\n"):
        # \n interno vira espaço: cada parágrafo canônico é uma linha
        flat = _normalize_line(block.replace("\n", " "))
        if flat:
            blocks.append(flat)
    return blocks


def build_ingest_result(raw_pages: list[str], title: str, kind: str) -> IngestResult:
    """Constrói o IngestResult: texto canônico NFC, parágrafos, capítulos,
    itens removidos e QualityReport."""
    cleaned_pages, removed, alerts = _clean_pages(raw_pages)
    blocks = [nfc(b) for b in _split_paragraph_blocks(_join_pages(cleaned_pages))]

    # texto canônico primeiro: parágrafos referenciam o source pelo id,
    # e o source referencia o texto pelo hash
    text = "\n\n".join(blocks)
    source = Source(title=title, kind=kind, content_hash=compute_text_hash(text))

    # Precedência de títulos: se a obra tem títulos explícitos (Capítulo N,
    # romanos), só eles numeram capítulos — folha de rosto, sumário e
    # subtítulos em maiúsculas viram parágrafos de texto, com alerta.
    # Sem nenhum título explícito, a regra de maiúsculas numera, com alerta.
    explicit = [_is_explicit_heading(b) for b in blocks]
    upper_only = [
        _is_uppercase_heading(b) and not e for b, e in zip(blocks, explicit)
    ]
    if any(explicit):
        is_heading = explicit
        for block, up in zip(blocks, upper_only):
            if up:
                alerts.append(
                    f'título em maiúsculas não numerado como capítulo: "{block[:60]}"'
                )
    else:
        is_heading = [e or u for e, u in zip(explicit, upper_only)]
        if any(upper_only):
            alerts.append(
                "capítulos detectados apenas pela regra de maiúsculas — confirmar na revisão"
            )

    paragraphs: list[Paragraph] = []
    chapters: list[ChapterSpan] = []
    offset = 0
    chapter: int | None = None
    number_in_chapter = 0

    for i, block in enumerate(blocks):
        if i > 0:
            offset += 2  # separador "\n\n"
        start, end = offset, offset + len(block)
        if is_heading[i]:
            if chapters:
                chapters[-1] = chapters[-1].model_copy(update={"end_offset": start})
            chapter = len(chapters) + 1
            chapters.append(
                ChapterSpan(index=chapter, title=block, start_offset=start, end_offset=end)
            )
            number_in_chapter = 0
            paragraphs.append(
                Paragraph(
                    source_id=source.id,
                    chapter=chapter,
                    number=0,
                    kind=ParagraphKind.titulo,
                    start_offset=start,
                    end_offset=end,
                )
            )
        else:
            number_in_chapter += 1
            paragraphs.append(
                Paragraph(
                    source_id=source.id,
                    chapter=chapter,
                    number=number_in_chapter,
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

    reason_counts = Counter(item.reason.value for item in removed)
    quality = QualityReport(
        pages=len(raw_pages),
        chapters_detected=len(chapters),
        paragraphs=len(paragraphs),
        removed_by_reason=dict(reason_counts),
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

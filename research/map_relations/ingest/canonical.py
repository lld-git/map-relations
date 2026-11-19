"""Rota pdf_loader da ingestão (fallback barato do Docling — ADR 008).

Converte páginas brutas de um parser em blocos MdBlock (com página, título e
alertas) para o Markdown intermediário. A montagem do IngestResult vive no
parser único (markdown.parse_markdown); build_ingest_result encadeia os dois.
"""

from __future__ import annotations

import re
from collections import Counter

from map_relations.core.ingest_contract import (
    IngestResult,
    ParagraphKind,
    RemovalReason,
    RemovedItem,
)

from .layout import _despace, is_explicit_heading  # noqa: F401 (re-exportados: docling_compare, alerts)
from .markdown import MdBlock, parse_markdown, render_markdown

# Linha repetida no início/fim de pelo menos esta fração das páginas é
# tratada como cabeçalho/rodapé.
_REPEAT_THRESHOLD = 0.6

_PAGE_NUMBER_RE = re.compile(r"^[\s\-–—]*\d{1,4}[\s\-–—]*$")


def _is_uppercase_heading(line: str) -> bool:
    """Linha curta toda em maiúsculas — candidata a título, menos confiável."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(line) >= 3


def _is_chapter_heading(line: str) -> bool:
    return is_explicit_heading(line) or _is_uppercase_heading(line)


def classify_headings(texts: list[str]) -> tuple[list[bool], list[str]]:
    """Precedência de títulos (genérica, sem regra de livro específico):
    com títulos explícitos, só eles numeram capítulos — maiúsculas viram texto
    com alerta; sem nenhum explícito, maiúsculas numeram, com alerta."""
    explicit = [is_explicit_heading(t) for t in texts]
    upper_only = [_is_uppercase_heading(t) and not e for t, e in zip(texts, explicit)]
    alerts: list[str] = []
    if any(explicit):
        for text, up in zip(texts, upper_only):
            if up:
                alerts.append(
                    f'título em maiúsculas não numerado como capítulo: "{text[:60]}"'
                )
        return explicit, alerts
    if any(upper_only):
        alerts.append(
            "capítulos detectados apenas pela regra de maiúsculas — confirmar na revisão"
        )
    return [e or u for e, u in zip(explicit, upper_only)], alerts


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


def pdf_pages_to_blocks(
    raw_pages: list[str],
) -> tuple[list[MdBlock], list[RemovedItem], list[str]]:
    """Conversor fallback: páginas brutas → blocos MdBlock com página.

    Mantém o comportamento histórico do pdf_loader: quebra de página é quebra
    de bloco, exceto quando a página termina com hífen (palavra atravessa)."""
    cleaned_pages, removed, alerts = _clean_pages(raw_pages)

    blocks: list[MdBlock] = []
    for page_no, page in enumerate(cleaned_pages, start=1):
        if not page:
            continue
        page_blocks = _split_paragraph_blocks(page)
        if not page_blocks:
            continue
        start = 0
        if blocks and blocks[-1].text.endswith("-"):
            # palavra atravessa a página: cola no bloco anterior
            blocks[-1].text = blocks[-1].text[:-1] + page_blocks[0]
            start = 1
        for text in page_blocks[start:]:
            blocks.append(MdBlock(text, page=page_no))

    is_heading, heading_alerts = classify_headings([b.text for b in blocks])
    for block, heading in zip(blocks, is_heading):
        if heading:
            block.kind = ParagraphKind.titulo
    alerts.extend(heading_alerts)
    return blocks, removed, alerts


def build_ingest_result(raw_pages: list[str], title: str, kind: str) -> IngestResult:
    """Rota pdf_loader completa: páginas → MdBlocks → documento.md → parser único."""
    blocks, removed, alerts = pdf_pages_to_blocks(raw_pages)
    md = render_markdown(blocks)
    return parse_markdown(
        md, title, kind, removed=removed, extra_alerts=alerts, pages=len(raw_pages)
    )

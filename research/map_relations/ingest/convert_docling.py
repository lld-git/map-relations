"""Conversor Docling: docling.json (cache) → blocos do Markdown intermediário.

O documento.md é sempre gerado a partir do docling.json, nunca do PDF
(ADR 008 §4). Títulos seguem a mesma precedência genérica da rota pdf_loader:
padrão explícito (Capítulo N, romanos) numera; section_header não explícito
logo após um título vira subtítulo; os demais viram texto com alerta.
"""

from __future__ import annotations

import re
from typing import Any

from map_relations.core.ingest_contract import (
    ParagraphKind,
    RemovalReason,
    RemovedItem,
)

from .canonical import is_explicit_heading
from .markdown import MdBlock

_HEADER_LABELS = {"title", "section_header"}
_EDGE_LABELS = {
    "page_header": RemovalReason.cabecalho,
    "page_footer": RemovalReason.rodape,
}


def _reading_order(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Itens de texto na ordem de leitura do body; fallback: ordem do array."""
    texts = doc.get("texts", [])
    by_ref = {f"#/texts/{i}": t for i, t in enumerate(texts)}
    groups = {f"#/groups/{i}": g for i, g in enumerate(doc.get("groups", []))}

    ordered: list[dict[str, Any]] = []

    def walk(children: list[dict[str, Any]]) -> None:
        for child in children:
            ref = child.get("$ref", "")
            if ref in by_ref:
                ordered.append(by_ref[ref])
            elif ref in groups:
                walk(groups[ref].get("children", []))
            # pictures/tables ignorados: conversão roda com tabelas e imagens
            # desligadas (ADR 008 §4)

    body = doc.get("body") or {}
    walk(body.get("children", []))
    return ordered if ordered else list(texts)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _first_page(item: dict[str, Any]) -> int | None:
    pages = [p.get("page_no") for p in item.get("prov", []) if p.get("page_no")]
    return min(pages) if pages else None


def docling_to_blocks(
    doc: dict[str, Any],
) -> tuple[list[MdBlock], list[RemovedItem], list[str], int]:
    """Retorna (blocos, removidos, alertas, páginas)."""
    removed: list[RemovedItem] = []
    alerts: list[str] = []
    blocks: list[MdBlock] = []

    items: list[tuple[str, str, int | None]] = []  # (label, texto, página)
    for item in _reading_order(doc):
        label = item.get("label", "text")
        text = _flat(item.get("text") or "")
        if not text:
            continue
        if label in _EDGE_LABELS:
            removed.append(
                RemovedItem(
                    page=_first_page(item) or 0, reason=_EDGE_LABELS[label], text=text
                )
            )
            continue
        items.append((label, text, _first_page(item)))

    has_explicit = any(is_explicit_heading(t) for _, t, _ in items)
    previous_was_title = False
    for label, text, page in items:
        if is_explicit_heading(text):
            blocks.append(MdBlock(text, ParagraphKind.titulo, page))
            previous_was_title = True
            continue
        if label in _HEADER_LABELS:
            if not has_explicit:
                blocks.append(MdBlock(text, ParagraphKind.titulo, page))
                previous_was_title = True
                continue
            if previous_was_title:
                blocks.append(MdBlock(text, ParagraphKind.subtitulo, page))
                previous_was_title = False
                continue
            alerts.append(f'título do layout não numerado como capítulo: "{text[:60]}"')
        blocks.append(MdBlock(text, ParagraphKind.texto, page))
        previous_was_title = False

    if not has_explicit and any(label in _HEADER_LABELS for label, _, _ in items):
        alerts.append(
            "capítulos vindos só do layout do Docling — confirmar na revisão"
        )

    pages = len(doc.get("pages", {}) or {})
    return blocks, removed, alerts, pages

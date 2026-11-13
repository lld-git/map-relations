"""Conversor Docling: docling.json (cache) → blocos do Markdown intermediário.

O documento.md é sempre gerado a partir do docling.json, nunca do PDF
(ADR 008 §4). Títulos seguem a mesma precedência genérica da rota pdf_loader:
padrão explícito (Capítulo N, romanos) numera; section_header não explícito
logo após um título vira subtítulo; os demais viram texto com alerta.

Conversão por faixas de páginas (B04c): cada faixa é um processo separado e
guarda seu docling.json (pages_XXXX-YYYY.json). DoclingDocument.concatenate
renumera as páginas — perde a página absoluta —, então a junção é feita aqui,
no nível dos itens: extrai cada faixa com página absoluta, aplica a regra de
parágrafo que atravessa página na fronteira e só então classifica (a
precedência de títulos precisa enxergar o documento inteiro)."""

from __future__ import annotations

import re
from dataclasses import dataclass
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
# pontuação que encerra parágrafo: se o item anterior termina assim, não é
# continuação de um parágrafo cortado na fronteira da faixa
_SENTENCE_END = ('.', '!', '?', ':', ';', '"', '»', ')', ']', '…')


@dataclass
class DoclingItem:
    label: str
    text: str
    page: int | None


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


def docling_items(
    doc: dict[str, Any],
) -> tuple[list[DoclingItem], list[RemovedItem], int]:
    """Extrai itens (sem classificar) com página absoluta e remoções de borda."""
    items: list[DoclingItem] = []
    removed: list[RemovedItem] = []
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
        items.append(DoclingItem(label, text, _first_page(item)))
    pages = len(doc.get("pages", {}) or {})
    return items, removed, pages


def items_to_blocks(items: list[DoclingItem]) -> tuple[list[MdBlock], list[str]]:
    """Classifica os itens já unidos em blocos (precedência global de títulos)."""
    blocks: list[MdBlock] = []
    alerts: list[str] = []
    has_explicit = any(is_explicit_heading(it.text) for it in items)
    previous_was_title = False
    for it in items:
        if is_explicit_heading(it.text):
            blocks.append(MdBlock(it.text, ParagraphKind.titulo, it.page))
            previous_was_title = True
            continue
        if it.label in _HEADER_LABELS:
            if not has_explicit:
                blocks.append(MdBlock(it.text, ParagraphKind.titulo, it.page))
                previous_was_title = True
                continue
            if previous_was_title:
                blocks.append(MdBlock(it.text, ParagraphKind.subtitulo, it.page))
                previous_was_title = False
                continue
            alerts.append(f'título do layout não numerado como capítulo: "{it.text[:60]}"')
        blocks.append(MdBlock(it.text, ParagraphKind.texto, it.page))
        previous_was_title = False

    if not has_explicit and any(it.label in _HEADER_LABELS for it in items):
        alerts.append(
            "capítulos vindos só do layout do Docling — confirmar na revisão"
        )
    return blocks, alerts


def _continues_paragraph(prev: str, nxt: str) -> bool:
    """O item anterior parece um parágrafo cortado que segue no próximo?
    Mesma ideia da regra de página do pdf_loader, aplicada na fronteira da faixa."""
    if not prev or not nxt:
        return False
    if prev.endswith("-"):
        return True
    return not prev.endswith(_SENTENCE_END) and nxt[:1].islower()


def _join_paragraph(prev: str, nxt: str) -> str:
    if prev.endswith("-"):
        return prev[:-1] + nxt  # palavra hifenizada atravessa a fronteira
    return f"{prev} {nxt}"


def merge_range_docs(
    docs: list[dict[str, Any]],
) -> tuple[list[MdBlock], list[RemovedItem], list[str], int]:
    """Junta faixas no nível dos itens, com página absoluta, aplicando a regra
    de parágrafo que atravessa página na fronteira entre faixas. Só depois
    classifica, para a precedência de títulos ver o documento inteiro."""
    merged: list[DoclingItem] = []
    removed: list[RemovedItem] = []
    total_pages = 0
    for doc in docs:
        items, rem, pages = docling_items(doc)
        removed.extend(rem)
        total_pages += pages
        if merged and items:
            prev, nxt = merged[-1], items[0]
            if (
                prev.label == "text"
                and nxt.label == "text"
                and _continues_paragraph(prev.text, nxt.text)
            ):
                merged[-1] = DoclingItem(
                    "text", _join_paragraph(prev.text, nxt.text), prev.page
                )
                items = items[1:]
        merged.extend(items)
    blocks, alerts = items_to_blocks(merged)
    return blocks, removed, alerts, total_pages


def docling_to_blocks(
    doc: dict[str, Any],
) -> tuple[list[MdBlock], list[RemovedItem], list[str], int]:
    """Faixa única: extrai, classifica e devolve (blocos, removidos, alertas, páginas)."""
    items, removed, pages = docling_items(doc)
    blocks, alerts = items_to_blocks(items)
    return blocks, removed, alerts, pages

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
precedência de títulos precisa enxergar o documento inteiro).

B04d (Opção B): os itens já chegam como LayoutItem da camada comum
(ingest/layout.py); o rótulo nativo do Docling é traduzido por
DOCLING_LABEL_MAP. Fase 5: cabeçalho/rodapé não são mais removidos na
extração (docling_items); a decisão é da regra da faixa do corpo
(layout.apply_body_band), calculada uma vez sobre o documento inteiro e
aplicada antes da junção de parágrafo entre faixas — só assim um falso
cabeçalho reclassificado para texto participa do join_crossing_items."""

from __future__ import annotations

import re
from typing import Any

from map_relations.core.ingest_contract import RemovedItem

from .layout import (
    LayoutItem,
    LayoutLabel,
    apply_body_band,
    classify_titles,
    compute_body_band,
    detect_chapter_subtitle_alerts,
    join_crossing_items,
    normalize_bbox,
    renumber,
    resolve_label,
)
from .markdown import MdBlock

# Mapa de rótulos nativos do Docling (docling_core.types.doc.labels.DocItemLabel,
# versão pinada no serviço — ADR B04d B.2) para LayoutLabel. Exaustivo: todo
# valor do enum tem entrada aqui (testado em test_layout.py, L4), para uma
# versão nova do Docling aparecer na revisão em vez de desaparecer em silêncio.
DOCLING_LABEL_MAP: dict[str, LayoutLabel] = {
    "title": LayoutLabel.titulo,
    "section_header": LayoutLabel.titulo,
    "text": LayoutLabel.texto,
    "paragraph": LayoutLabel.texto,
    "list_item": LayoutLabel.lista,
    "marker": LayoutLabel.lista,
    "page_header": LayoutLabel.cabecalho,
    "page_footer": LayoutLabel.rodape,
    "footnote": LayoutLabel.nota,
    "caption": LayoutLabel.nota,
    "table": LayoutLabel.tabela,
    "picture": LayoutLabel.figura,
    "chart": LayoutLabel.figura,
    "formula": LayoutLabel.texto,
    "code": LayoutLabel.texto,
    "document_index": LayoutLabel.texto,
    "reference": LayoutLabel.texto,
    "checkbox_selected": LayoutLabel.desconhecido,
    "checkbox_unselected": LayoutLabel.desconhecido,
    "form": LayoutLabel.desconhecido,
    "key_value_region": LayoutLabel.desconhecido,
    "field_heading": LayoutLabel.desconhecido,
    "field_hint": LayoutLabel.desconhecido,
    "field_item": LayoutLabel.desconhecido,
    "field_key": LayoutLabel.desconhecido,
    "field_region": LayoutLabel.desconhecido,
    "field_value": LayoutLabel.desconhecido,
    "empty_value": LayoutLabel.desconhecido,
    "grading_scale": LayoutLabel.desconhecido,
    "handwritten_text": LayoutLabel.desconhecido,
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


def _page_sizes(doc: dict[str, Any]) -> dict[int, tuple[float, float]]:
    sizes: dict[int, tuple[float, float]] = {}
    for key, page in (doc.get("pages") or {}).items():
        size = (page or {}).get("size") or {}
        if "width" in size and "height" in size:
            sizes[int(key)] = (size["width"], size["height"])
    return sizes


def _item_bbox(item: dict[str, Any], page_sizes: dict[int, tuple[float, float]]) -> Any:
    """bbox normalizada do primeiro prov com bbox e tamanho de página conhecido;
    None quando falta geometria (sempre o caso hoje: a conversão roda com
    page-batch-size 1 e os JSONs sintéticos de teste não têm bbox nem size)."""
    for prov in item.get("prov", []):
        bbox = prov.get("bbox")
        page_no = prov.get("page_no")
        if not bbox or page_no not in page_sizes:
            continue
        width, height = page_sizes[page_no]
        return normalize_bbox(
            left=bbox.get("l", 0),
            top=bbox.get("t", 0),
            right=bbox.get("r", 0),
            bottom=bbox.get("b", 0),
            page_width=width,
            page_height=height,
        )
    return None


def docling_items(
    doc: dict[str, Any],
) -> tuple[list[LayoutItem], list[str], int]:
    """Extrai itens (sem classificar, sem remover moldura — fase 5: essa
    decisão é da regra da faixa do corpo, layout.apply_body_band, que
    precisa ver o item antes de decidir)."""
    items: list[LayoutItem] = []
    alerts: list[str] = []
    page_sizes = _page_sizes(doc)
    order = 0
    for item in _reading_order(doc):
        source_label = item.get("label", "text")
        text = _flat(item.get("text") or "")
        if not text:
            continue
        label, alert = resolve_label(source_label, DOCLING_LABEL_MAP)
        if alert:
            alerts.append(alert)
        items.append(
            LayoutItem(
                order=order,
                label=label,
                text=text,
                source_label=source_label,
                converter="docling",
                page=_first_page(item),
                bbox=_item_bbox(item, page_sizes),
                marker=item.get("marker"),
                level=item.get("level"),
                furniture_hint=item.get("content_layer") == "furniture",
            )
        )
        order += 1
    pages = len(doc.get("pages", {}) or {})
    return items, alerts, pages


def _block_text(item: LayoutItem) -> str:
    """Texto do bloco: item de lista leva o marcador do Docling na frente
    (ex. "- fala"), senão o travessão ou hífen de fala da obra se perde —
    `LayoutItem.marker` já chega preenchido de `docling_items`."""
    if item.label is LayoutLabel.lista and item.marker:
        return f"{item.marker} {item.text}"
    return item.text


def items_to_blocks(items: list[LayoutItem]) -> tuple[list[MdBlock], list[str]]:
    """Classifica os itens já unidos em blocos (precedência global de títulos,
    delegada a layout.classify_titles) e detecta subtítulo de capítulo
    suspeito (B04e, layout.detect_chapter_subtitle_alerts)."""
    kinds, title_alerts = classify_titles(items)
    alerts = detect_chapter_subtitle_alerts(items) + title_alerts
    blocks = [MdBlock(_block_text(it), kind, it.page) for it, kind in zip(items, kinds)]
    return blocks, alerts


def merged_layout_items(
    docs: list[dict[str, Any]],
) -> tuple[list[LayoutItem], list[RemovedItem], list[str], int]:
    """Itens de layout já com a faixa do corpo aplicada (fase 5) e unidos
    entre faixas (join_crossing_items), com página absoluta — antes da
    classificação de títulos. A faixa do corpo é calculada uma só vez sobre
    o documento inteiro — nunca por faixa de página (B04c) — e só então
    aplicada a cada faixa; a junção de parágrafo que atravessa página na
    fronteira entre faixas usa as faixas já limpas pela regra do corpo (um
    falso cabeçalho reclassificado para texto passa a poder ser unido à
    frase anterior). Extraído de `merge_range_docs` (fase 6, B04d): é a
    mesma representação comum que `pdf_loader.layout_items`, usada por
    `make compare` para comparar qualquer conversor registrado sobre o
    mesmo nível (LayoutItem), em vez do formato nativo de um conversor
    específico."""
    item_alerts: list[str] = []
    total_pages = 0
    ranges: list[list[LayoutItem]] = []
    for doc in docs:
        items, alerts, pages = docling_items(doc)
        item_alerts.extend(alerts)
        total_pages += pages
        ranges.append(items)

    band = compute_body_band([it for r in ranges for it in r])
    removed: list[RemovedItem] = []
    band_ranges: list[list[LayoutItem]] = []
    for r in ranges:
        kept, rem, alerts = apply_body_band(r, band)
        band_ranges.append(kept)
        removed.extend(rem)
        item_alerts.extend(alerts)

    merged = renumber(join_crossing_items(band_ranges))
    return merged, removed, item_alerts, total_pages


def merge_range_docs(
    docs: list[dict[str, Any]],
) -> tuple[list[MdBlock], list[RemovedItem], list[str], int]:
    """Junta faixas no nível dos itens, com página absoluta, e classifica
    títulos (precedência global, só depois de ver o documento inteiro)."""
    merged, removed, item_alerts, total_pages = merged_layout_items(docs)
    blocks, block_alerts = items_to_blocks(merged)
    return blocks, removed, item_alerts + block_alerts, total_pages


def docling_to_blocks(
    doc: dict[str, Any],
) -> tuple[list[MdBlock], list[RemovedItem], list[str], int]:
    """Faixa única: extrai, aplica a regra da faixa do corpo (fase 5),
    classifica e devolve (blocos, removidos, alertas, páginas)."""
    items, item_alerts, pages = docling_items(doc)
    band_items, removed, band_alerts = apply_body_band(items)
    blocks, block_alerts = items_to_blocks(band_items)
    return blocks, removed, item_alerts + band_alerts + block_alerts, pages

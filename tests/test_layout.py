"""Camada comum de layout (B04d, Opção B): BBox, LayoutLabel, LayoutItem
(fase 0) e o mapa de rótulos do adaptador Docling (fase 1)."""

from docling_core.types.doc.labels import DocItemLabel

from map_relations.ingest.convert_docling import DOCLING_LABEL_MAP
from map_relations.ingest.layout import (
    LayoutItem,
    LayoutLabel,
    normalize_bbox,
    renumber,
    resolve_label,
)


def test_bbox_bottomleft_footer_item_has_top_near_one():
    # Docling: origem inferior, página 800pt de altura; item a 20pt do fundo.
    bbox = normalize_bbox(left=100, top=34, right=300, bottom=20, page_width=600, page_height=800)
    assert bbox.top > 0.95
    assert bbox.bottom > 0.95


def test_bbox_fraction_comparable_across_page_sizes():
    # mesma posição relativa (10% do topo) em páginas de tamanhos diferentes.
    small = normalize_bbox(left=0, top=720, right=100, bottom=700, page_width=200, page_height=800)
    big = normalize_bbox(left=0, top=1440, right=200, bottom=1400, page_width=400, page_height=1600)
    assert round(small.top, 2) == round(big.top, 2)


def test_layout_item_without_bbox_or_page_is_valid():
    item = LayoutItem(
        order=0, label=LayoutLabel.texto, text="texto", source_label="text", converter="txt"
    )
    assert item.bbox is None
    assert item.page is None


def test_resolve_label_unknown_native_label_becomes_desconhecido_with_alert():
    label, alert = resolve_label("qualquer_coisa_nova", {"text": LayoutLabel.texto})
    assert label is LayoutLabel.desconhecido
    assert alert is not None
    assert "qualquer_coisa_nova" in alert


def test_resolve_label_known_native_label_has_no_alert():
    label, alert = resolve_label("text", {"text": LayoutLabel.texto})
    assert label is LayoutLabel.texto
    assert alert is None


def test_renumber_makes_order_contiguous_regardless_of_input():
    def item(order: int, text: str) -> LayoutItem:
        return LayoutItem(
            order=order, label=LayoutLabel.texto, text=text,
            source_label="text", converter="docling",
        )

    items = [item(5, "a"), item(5, "b"), item(0, "c")]
    out = renumber(items)
    assert [it.order for it in out] == [0, 1, 2]
    assert [it.text for it in out] == ["a", "b", "c"]  # ordem da lista preservada


# ── L4: mapa de rótulos do Docling (B.2) ─────────────────────────────────────


def test_docling_label_map_covers_every_doc_item_label():
    """Exaustividade: uma versão nova do Docling com rótulo novo deve falhar
    aqui, não desaparecer em silêncio via resolve_label/desconhecido."""
    native_labels = {member.value for member in DocItemLabel}
    assert native_labels == set(DOCLING_LABEL_MAP)


def test_docling_label_map_matches_table_b2():
    expected = {
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
        "empty_value": LayoutLabel.desconhecido,
        "grading_scale": LayoutLabel.desconhecido,
        "handwritten_text": LayoutLabel.desconhecido,
    }
    for native, label in expected.items():
        assert DOCLING_LABEL_MAP[native] is label

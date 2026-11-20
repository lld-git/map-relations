"""Regra nova da Opção A (B04d, fase 5): faixa do corpo, sobre LayoutItem[].

Convenção de BBox (ingest/layout.py): fração de página, origem no topo —
`top`/`bottom` próximos de 0 é o topo da página, próximos de 1 é o rodapé.
"""

from map_relations.core.ingest_contract import RemovalReason
from map_relations.ingest.layout import (
    BBox,
    LayoutItem,
    LayoutLabel,
    apply_body_band,
    compute_body_band,
)


def _item(
    order: int,
    text: str,
    label: LayoutLabel,
    page: int,
    top: float,
    bottom: float,
) -> LayoutItem:
    return LayoutItem(
        order=order,
        label=label,
        text=text,
        source_label="native",
        converter="docling",
        page=page,
        bbox=BBox(top=top, bottom=bottom, left=0.1, right=0.9),
    )


def _body_pages(n: int) -> list[LayoutItem]:
    """n páginas de corpo típico (faixa 0.1–0.9), uma frase por página."""
    return [
        _item(i, f"Frase do corpo da página {i + 1}.", LayoutLabel.texto, i + 1, 0.1, 0.2)
        for i in range(n)
    ]


def test_false_header_inside_body_band_becomes_text_in_place():
    """F1: falso cabeçalho (bbox dentro da faixa do corpo) volta a ser
    texto, na posição original — não é removido, nem reordenado."""
    items = _body_pages(4)
    # "K." rotulado como page_header pelo Docling, mas geometricamente
    # dentro da faixa do corpo (igual às frases normais da página).
    false_header = _item(10, "K.", LayoutLabel.cabecalho, 3, 0.1, 0.15)
    items = items[:2] + [false_header] + items[2:]

    kept, removed, alerts = apply_body_band(items)

    assert [it.text for it in kept] == [
        "Frase do corpo da página 1.",
        "Frase do corpo da página 2.",
        "K.",
        "Frase do corpo da página 3.",
        "Frase do corpo da página 4.",
    ]
    assert kept[2].label is LayoutLabel.texto
    assert removed == []
    # reclassificação registrada para o report.md (critério de pronto do B04d)
    assert any("volta a ser texto" in a and "K." in a for a in alerts)


def test_real_header_above_body_band_stays_removed():
    """F2: cabeçalho real, acima da faixa do corpo, continua removido."""
    items = _body_pages(4)
    real_header = _item(10, "O Processo — Franz Kafka", LayoutLabel.cabecalho, 3, 0.0, 0.03)
    items = items[:2] + [real_header] + items[2:]

    kept, removed, _ = apply_body_band(items)

    assert "O Processo — Franz Kafka" not in [it.text for it in kept]
    assert len(removed) == 1
    assert removed[0].reason is RemovalReason.cabecalho
    assert removed[0].page == 3


def test_page_number_below_body_band_removed_even_labeled_text():
    """F3: número de página abaixo da faixa é removido como numero_pagina,
    mesmo chegando com rótulo nativo "text" (não page_footer)."""
    items = _body_pages(4)
    page_number = _item(10, "3", LayoutLabel.texto, 3, 0.95, 0.98)
    items = items[:2] + [page_number] + items[2:]

    kept, removed, _ = apply_body_band(items)

    assert "3" not in [it.text for it in kept]
    assert len(removed) == 1
    assert removed[0].reason is RemovalReason.numero_pagina
    assert removed[0].page == 3


def test_number_in_middle_of_body_band_is_kept():
    """F4: número no meio do texto, dentro da faixa do corpo, é mantido —
    é conteúdo (citação, por exemplo), não número de página."""
    items = _body_pages(4)
    inline_number = _item(10, "42", LayoutLabel.texto, 3, 0.15, 0.18)
    items = items[:2] + [inline_number] + items[2:]

    kept, removed, _ = apply_body_band(items)

    assert "42" in [it.text for it in kept]
    assert removed == []


def test_short_document_keeps_current_behaviour_with_alert():
    """F5: documento com poucas páginas (faixa não confiável) mantém o
    comportamento de antes da fase 5 — cabeçalho/rodapé sempre removidos —
    e gera alerta em vez de arriscar um corte sem base estatística."""
    items = _body_pages(2) + [
        _item(10, "Cabeçalho", LayoutLabel.cabecalho, 1, 0.0, 0.03),
        _item(11, "Rodapé", LayoutLabel.rodape, 2, 0.95, 0.98),
    ]

    kept, removed, alerts = apply_body_band(items)

    assert {it.text for it in kept} == {it.text for it in _body_pages(2)}
    assert {r.reason for r in removed} == {RemovalReason.cabecalho, RemovalReason.rodape}
    assert any("faixa do corpo não confiável" in a for a in alerts)


def test_items_without_bbox_fall_back_to_repetition_rule_unaffected():
    """F6: itens sem bbox (rota pdf_loader) ignoram a faixa — nada no
    pdf_loader passa por apply_body_band; aqui confere-se diretamente que
    um item de moldura sem bbox, nesta função, cai no mesmo fallback
    incondicional (cabecalho/rodape removidos, resto intocado), em vez de
    ser silenciosamente mantido por falta de geometria."""
    band = compute_body_band(_body_pages(4))  # faixa confiável
    assert band.confident
    items = [
        LayoutItem(
            order=0, label=LayoutLabel.cabecalho, text="Cabeçalho",
            source_label="page_header", converter="pdf_loader", page=1,
        ),
        LayoutItem(
            order=1, label=LayoutLabel.texto, text="Texto normal.",
            source_label="line", converter="pdf_loader", page=1,
        ),
    ]
    kept, removed, _ = apply_body_band(items, band)
    assert [it.text for it in kept] == ["Texto normal."]
    assert removed[0].reason is RemovalReason.cabecalho


def test_apply_body_band_has_no_effect_without_page():
    """E3 (equivalência entre conversores, plano B04d): page=None (TXT,
    pandoc) não dispara a regra da faixa. `layout_items_to_blocks` (usado
    por esses dois conversores) nunca chama `apply_body_band` — só
    pdf_loader e Docling o fazem —, mas mesmo chamada direto ela não
    altera nada sem página: sem página não há "dentro/fora da faixa"."""
    items = [
        LayoutItem(
            order=0, label=LayoutLabel.texto, text="Parágrafo qualquer.",
            source_label="paragraph", converter="txt",
        ),
        LayoutItem(
            order=1, label=LayoutLabel.texto, text="Outro parágrafo.",
            source_label="paragraph", converter="txt",
        ),
    ]
    kept, removed, _ = apply_body_band(items)
    assert kept == items
    assert removed == []


def test_band_computed_once_over_whole_document_not_per_range():
    """F7: duas faixas de página (B04c) com margens diferentes produzem um
    único corte sobre o documento inteiro, não um por faixa — senão o
    corte mudaria de página para página."""
    range_a = [
        _item(i, f"Corpo A{i}.", LayoutLabel.texto, i + 1, 0.10, 0.20) for i in range(3)
    ]
    range_b = [
        _item(i, f"Corpo B{i}.", LayoutLabel.texto, i + 4, 0.30, 0.40) for i in range(3)
    ]
    band_whole_doc = compute_body_band(range_a + range_b)
    band_a_only = compute_body_band(range_a)
    band_b_only = compute_body_band(range_b)

    assert band_whole_doc.confident
    # o corte do documento inteiro não coincide com o de nenhuma faixa
    # isolada — provando que não é soma/concatenação de cortes por faixa.
    assert (band_whole_doc.top, band_whole_doc.bottom) != (
        band_a_only.top,
        band_a_only.bottom,
    )
    assert (band_whole_doc.top, band_whole_doc.bottom) != (
        band_b_only.top,
        band_b_only.bottom,
    )

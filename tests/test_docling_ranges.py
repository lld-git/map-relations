"""Conversão do Docling por faixas: junção no nível dos itens com página
absoluta e regra de parágrafo que atravessa a fronteira (B04c)."""

from map_relations.core.ingest_contract import ParagraphKind
from map_relations.ingest.convert_docling import merge_range_docs
from map_relations.ingest.markdown import parse_markdown, render_markdown
from map_relations.ingest.pdf_loader import page_ranges


def _doc(pages: list[int], texts: list[tuple[str, str, int]]) -> dict:
    """texts: lista de (label, texto, página). body na ordem dada."""
    return {
        "pages": {str(p): {} for p in pages},
        "body": {"children": [{"$ref": f"#/texts/{i}"} for i in range(len(texts))]},
        "texts": [
            {"label": lbl, "text": txt, "prov": [{"page_no": pg}]}
            for lbl, txt, pg in texts
        ],
    }


# ── page_ranges ───────────────────────────────────────────────────────────────


def test_page_ranges_default():
    assert page_ranges(90, 40) == [(1, 40), (41, 80), (81, 90)]
    assert page_ranges(40, 40) == [(1, 40)]
    assert page_ranges(0, 40) == []


# ── fronteira entre faixas ────────────────────────────────────────────────────


def test_paragraph_cut_mid_sentence_is_rejoined():
    # parágrafo cortado: faixa A termina sem pontuação final, faixa B começa minúsculo
    a = _doc([1, 2], [("text", "Josef K. aguardou em silêncio e o caso seguiu sem", 2)])
    b = _doc([3, 4], [("text", "resolução por semanas a fio.", 3)])
    blocks, _, _, pages = merge_range_docs([a, b])
    assert pages == 4
    textos = [x.text for x in blocks if x.kind is ParagraphKind.texto]
    assert textos == [
        "Josef K. aguardou em silêncio e o caso seguiu sem resolução por semanas a fio."
    ]
    # não ficou partido em dois
    assert "Josef K. aguardou em silêncio e o caso seguiu sem" not in textos


def test_hyphen_at_boundary_is_dehyphenated():
    a = _doc([1, 2], [("text", "Foi um primeiro inter-", 2)])
    b = _doc([3, 4], [("text", "rogatório demorado.", 3)])
    blocks, _, _, _ = merge_range_docs([a, b])
    textos = [x.text for x in blocks if x.kind is ParagraphKind.texto]
    assert "Foi um primeiro interrogatório demorado." in textos


def test_complete_sentence_at_boundary_stays_split():
    a = _doc([1, 2], [("text", "Terminava ali o primeiro dia.", 2)])
    b = _doc([3, 4], [("text", "Na manhã seguinte tudo recomeçou.", 3)])
    blocks, _, _, _ = merge_range_docs([a, b])
    textos = [x.text for x in blocks if x.kind is ParagraphKind.texto]
    assert "Terminava ali o primeiro dia." in textos
    assert "Na manhã seguinte tudo recomeçou." in textos


def test_title_at_boundary_never_joined():
    a = _doc([1, 2], [("text", "fim do trecho sem ponto", 2)])
    b = _doc([3, 4], [("section_header", "Capítulo II", 3)])
    blocks, _, _, _ = merge_range_docs([a, b])
    assert any(x.kind is ParagraphKind.titulo and x.text == "Capítulo II" for x in blocks)


def _doc_with_bbox(pages: list[int], items: list[tuple[str, str, int]]) -> dict:
    """Como `_doc`, mas com bbox e tamanho de página — necessário para a
    regra da faixa do corpo (fase 5) decidir algo; todos os itens usam a
    mesma bbox (dentro da faixa típica de corpo), já que o que varia entre
    eles aqui é o rótulo nativo, não a posição."""
    return {
        "pages": {str(p): {"size": {"width": 600, "height": 800}} for p in pages},
        "body": {"children": [{"$ref": f"#/texts/{i}"} for i in range(len(items))]},
        "texts": [
            {
                "label": lbl,
                "text": txt,
                "prov": [{"page_no": pg, "bbox": {"l": 100, "t": 700, "r": 500, "b": 680}}],
            }
            for lbl, txt, pg in items
        ],
    }


def test_false_header_at_page_start_rejoins_cut_sentence_e2():
    """E2 ponta a ponta (plano B04d): página A termina sem pontuação final
    com "... ela finalmente disse"; página B abre com "K." rotulado
    page_header pelo Docling mas geometricamente dentro da faixa do corpo —
    a regra da faixa (fase 5) reclassifica para texto, na posição original,
    e só então a junção de parágrafo (decisão do E2) o une ao anterior
    apesar de "K." começar com maiúscula: "... ela finalmente disse K."."""
    a = _doc_with_bbox(
        [1, 2, 3],
        [
            ("text", "Primeira frase de preenchimento do corpo.", 1),
            ("text", "Segunda frase de preenchimento do corpo.", 2),
            (
                "text",
                "O interrogatório prosseguiu até que, cansada, ela finalmente disse",
                3,
            ),
        ],
    )
    b = _doc_with_bbox(
        [4],
        [
            ("page_header", "K.", 4),
            ("text", "Mas ninguém respondeu.", 4),
        ],
    )
    blocks, removed, alerts, _ = merge_range_docs([a, b])
    textos = [x.text for x in blocks]
    assert (
        "O interrogatório prosseguiu até que, cansada, ela finalmente disse K."
        in textos
    )
    assert "Mas ninguém respondeu." in textos
    assert removed == []  # "K." não foi removido como cabeçalho: ficou dentro da faixa
    assert any("volta a ser texto" in a and "K." in a for a in alerts)


# ── classificação global entre faixas ─────────────────────────────────────────


def test_explicit_heading_in_later_range_demotes_earlier_uppercase():
    # faixa A só tem um section_header em maiúsculas; faixa B tem título explícito.
    # globalmente, só o explícito numera (A vira texto, não capítulo).
    a = _doc([1], [("section_header", "PREFÁCIO", 1), ("text", "Texto do prefácio.", 1)])
    b = _doc([2], [("section_header", "Capítulo I", 2), ("text", "Começa a obra.", 2)])
    blocks, _, _, _ = merge_range_docs([a, b])
    titulos = [x.text for x in blocks if x.kind is ParagraphKind.titulo]
    assert titulos == ["Capítulo I"]
    assert any(
        x.text == "PREFÁCIO" and x.kind is ParagraphKind.texto for x in blocks
    )


def test_merged_blocks_feed_single_parser_with_absolute_pages():
    a = _doc([1, 2], [("section_header", "Capítulo I", 1), ("text", "Primeiro.", 2)])
    b = _doc([3], [("text", "Segundo parágrafo.", 3)])
    blocks, _removed, _alerts, pages = merge_range_docs([a, b])
    r = parse_markdown(render_markdown(blocks), "t", "pdf", pages=pages)
    assert r.quality.chapters_detected == 1
    assert r.paragraphs[0].page == 1
    assert r.paragraphs[-1].page == 3

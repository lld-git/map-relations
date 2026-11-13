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

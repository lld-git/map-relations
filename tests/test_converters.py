"""Conversores → MdBlocks: Docling (JSON sintético), TXT e pandoc (HTML)."""

import shutil

import pytest

from map_relations.core.ingest_contract import ParagraphKind, RemovalReason
from map_relations.ingest.convert_docling import docling_to_blocks
from map_relations.ingest.convert_pandoc import convert_pandoc, pandoc_md_to_blocks
from map_relations.ingest.convert_txt import txt_to_blocks
from map_relations.ingest.markdown import parse_markdown, render_markdown

DOCLING_DOC = {
    "pages": {"1": {}, "2": {}},
    "body": {
        "children": [
            {"$ref": "#/texts/0"},
            {"$ref": "#/texts/1"},
            {"$ref": "#/texts/2"},
            {"$ref": "#/texts/3"},
            {"$ref": "#/texts/4"},
            {"$ref": "#/texts/5"},
        ]
    },
    "texts": [
        {"label": "page_header", "text": "O Processo — Kafka", "prov": [{"page_no": 1}]},
        {"label": "section_header", "text": "C A P Í T U L O I", "prov": [{"page_no": 1}]},
        {
            "label": "section_header",
            "text": "A Visita. Conversa com a senhora Grubach",
            "prov": [{"page_no": 1}],
        },
        {"label": "text", "text": "Josef K. entrou na sala.", "prov": [{"page_no": 1}]},
        {"label": "section_header", "text": "NO ESCRITÓRIO", "prov": [{"page_no": 2}]},
        {"label": "text", "text": "K. foi até a catedral.", "prov": [{"page_no": 2}]},
    ],
}


def test_docling_blocks_titles_subtitles_and_removed():
    blocks, removed, alerts, pages = docling_to_blocks(DOCLING_DOC)
    assert pages == 2
    assert [b.kind for b in blocks] == [
        ParagraphKind.titulo,      # C A P Í T U L O I (explícito via despace)
        ParagraphKind.subtitulo,   # section_header logo após o título
        ParagraphKind.texto,
        ParagraphKind.texto,       # NO ESCRITÓRIO: header não explícito, sem título antes
        ParagraphKind.texto,
    ]
    assert removed[0].reason is RemovalReason.cabecalho
    assert any("NO ESCRITÓRIO" in a for a in alerts)


def test_docling_blocks_feed_single_parser():
    blocks, removed, alerts, pages = docling_to_blocks(DOCLING_DOC)
    r = parse_markdown(
        render_markdown(blocks), "t", "pdf",
        removed=removed, extra_alerts=alerts, pages=pages,
    )
    assert r.quality.chapters_detected == 1
    assert r.locate(r.text.index("A Visita.")) == "cap. 1, subtítulo"
    assert r.locate(r.text.index("Josef K. entrou")) == "cap. 1, § 1"
    assert r.paragraphs[0].page == 1
    assert r.paragraphs[-1].page == 2


def test_docling_uppercase_headers_number_when_no_explicit():
    doc = {
        "pages": {"1": {}},
        "texts": [
            {"label": "section_header", "text": "A PARTIDA", "prov": [{"page_no": 1}]},
            {"label": "text", "text": "Um texto.", "prov": [{"page_no": 1}]},
        ],
    }
    blocks, _, alerts, _ = docling_to_blocks(doc)
    assert blocks[0].kind is ParagraphKind.titulo
    assert any("layout do Docling" in a for a in alerts)


def test_txt_blocks():
    blocks, removed, alerts = txt_to_blocks(
        "Capítulo I\n\nJosef K. entrou na sala.\n\nOutro parágrafo."
    )
    assert blocks[0].kind is ParagraphKind.titulo
    assert len(blocks) == 3
    assert removed == []


def test_pandoc_md_to_blocks_headings_and_unescape():
    md = "# Capítulo I\n\nTexto com escape pandoc: 5\\*, \\# e \\[x\\].\n"
    blocks, _, _ = pandoc_md_to_blocks(md)
    assert blocks[0].kind is ParagraphKind.titulo
    assert blocks[1].text == "Texto com escape pandoc: 5*, # e [x]."


@pytest.mark.skipif(shutil.which("pandoc") is None, reason="pandoc não instalado")
def test_pandoc_converts_html(tmp_path):
    html = tmp_path / "doc.html"
    html.write_text(
        "<h1>Capítulo I</h1><p>Josef K. entrou na sala.</p><p>Outro parágrafo.</p>",
        encoding="utf-8",
    )
    blocks, _, _ = convert_pandoc(html)
    assert blocks[0].kind is ParagraphKind.titulo
    assert blocks[0].text == "Capítulo I"
    assert blocks[1].text == "Josef K. entrou na sala."

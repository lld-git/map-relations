"""Parser único do Markdown intermediário (ADR 008): convenção, escape,
marcadores de página e subtítulo."""

from map_relations.core.ingest_contract import ParagraphKind
from map_relations.ingest.markdown import (
    MdBlock,
    escape_md,
    parse_markdown,
    render_markdown,
    unescape_md,
)

MD = """\
<!-- p.1 -->

# Capítulo I

*A Visita. Conversa com a senhora Grubach*

Josef K. entrou na sala.

<!-- p.2 -->

A cozinheira não apareceu.

# Capítulo II

O inquérito começou cedo.
"""


def test_parse_builds_chapters_subtitles_and_pages():
    r = parse_markdown(MD, title="t", kind="pdf")
    assert r.quality.chapters_detected == 2
    by_kind = {(p.chapter, p.kind): p for p in r.paragraphs}
    assert by_kind[(1, ParagraphKind.titulo)].page == 1
    assert by_kind[(1, ParagraphKind.subtitulo)].number == 0
    assert r.locate(r.text.index("A Visita.")) == "cap. 1, subtítulo"
    assert r.locate(r.text.index("Josef K. entrou")) == "cap. 1, § 1"
    assert r.locate(r.text.index("A cozinheira")) == "cap. 1, § 2"
    assert r.locate(r.text.index("O inquérito")) == "cap. 2, § 1"


def test_page_markers_tracked_and_not_in_canonical():
    r = parse_markdown(MD, title="t", kind="pdf")
    assert "<!--" not in r.text
    pages = {
        r.text[p.start_offset : p.start_offset + 12]: p.page for p in r.paragraphs
    }
    assert pages["A cozinheira"] == 2
    assert r.quality.pages == 2  # derivado do último marcador


def test_subtitle_only_right_after_title():
    md = "# Capítulo I\n\nTexto.\n\n*linha em itálico solta*\n"
    r = parse_markdown(md, title="t", kind="txt")
    kinds = [p.kind for p in r.paragraphs]
    assert ParagraphKind.subtitulo not in kinds  # itálico longe do título = texto


def test_escape_roundtrip():
    original = "Nota 5* do cap. #3: a\\b e um <!-- comentário -->"
    assert unescape_md(escape_md(original)) == original


def test_escaped_content_is_not_interpreted():
    blocks = [
        MdBlock("# não sou título", ParagraphKind.texto),
        MdBlock("*não sou subtítulo*", ParagraphKind.texto),
        MdBlock("<!-- p.99 --> não sou marcador", ParagraphKind.texto),
    ]
    r = parse_markdown(render_markdown(blocks), title="t", kind="txt")
    assert r.quality.chapters_detected == 0
    assert "# não sou título" in r.text
    assert "*não sou subtítulo*" in r.text
    assert "<!-- p.99 --> não sou marcador" in r.text
    assert all(p.page is None for p in r.paragraphs)


def test_render_parse_roundtrip_preserves_structure():
    blocks = [
        MdBlock("Capítulo I", ParagraphKind.titulo, page=1),
        MdBlock("Resumo do capítulo", ParagraphKind.subtitulo, page=1),
        MdBlock("Primeiro parágrafo.", ParagraphKind.texto, page=1),
        MdBlock("Segundo parágrafo.", ParagraphKind.texto, page=2),
    ]
    r = parse_markdown(render_markdown(blocks), title="t", kind="pdf")
    assert [p.kind for p in r.paragraphs] == [
        ParagraphKind.titulo,
        ParagraphKind.subtitulo,
        ParagraphKind.texto,
        ParagraphKind.texto,
    ]
    assert [p.page for p in r.paragraphs] == [1, 1, 1, 2]


def test_human_edit_changes_canonical_hash():
    """Regra de integridade do ADR 008: editar o .md muda o hash canônico."""
    before = parse_markdown(MD, title="t", kind="pdf")
    after = parse_markdown(MD.replace("Josef K. entrou na sala.", "Josef K. saiu da sala."),
                           title="t", kind="pdf")
    assert before.source.content_hash != after.source.content_hash

"""B04: IngestResult, texto canônico, locate() e relatório de revisão."""

import pytest

from map_relations.core.ingest_contract import ParagraphKind, RemovalReason
from map_relations.core.protocols import DocumentParser
from map_relations.ingest.canonical import build_ingest_result
from map_relations.ingest.pdf_loader import PdfParser
from map_relations.ingest.report import render_report, write_processed

HEADER = "O Processo — Franz Kafka"

PAGES = [
    (
        f"{HEADER}\n"
        "Documento interno de teste.\n"
        "\n"
        "Capítulo I\n"
        "Josef K. aguardava quando recebeu a convo-\n"
        "1"
    ),
    (
        f"{HEADER}\n"
        "cação para comparecer. A senhora Grubach observava da porta.\n"
        "\n"
        "K. esperou sentado à mesa.\n"
        "2"
    ),
    (
        f"{HEADER}\n"
        "Capítulo II\n"
        "K. recebeu aviso de que na manhã seguinte haveria um pe-\n"
        "queno interrogatório sobre o seu caso.\n"
        "3"
    ),
    (
        f"{HEADER}\n"
        "O interrogatório começou cedo.\n"
        "4"
    ),
]


@pytest.fixture(scope="module")
def result():
    return build_ingest_result(PAGES, title="processo-teste", kind="pdf")


# ── texto canônico ────────────────────────────────────────────────────────────


def test_header_and_page_numbers_removed(result):
    assert HEADER not in result.text
    reasons = [r.reason for r in result.removed]
    assert reasons.count(RemovalReason.cabecalho) == 4
    assert reasons.count(RemovalReason.numero_pagina) == 4


def test_hyphenation_joined_across_pages(result):
    assert "convocação para comparecer" in result.text
    assert "convo- cação" not in result.text and "convo-cação" not in result.text


def test_hyphenation_joined_within_page(result):
    assert "pequeno interrogatório" in result.text


def test_proper_noun_at_page_start_rejoins_cut_sentence_e2():
    """E2 ponta a ponta, rota pdf_loader (sem bbox, por repetição): "K."
    como primeira linha da página 2 nunca é removido como cabeçalho — não
    se repete em nenhuma outra página, então a regra de repetição
    (`layout.drop_page_furniture`) não o toca —, e a junção de parágrafo
    (decisão do E2) o une à frase sem pontuação final da página anterior
    apesar de começar com maiúscula (nome próprio)."""
    pages = [
        "O interrogatório prosseguiu até que, cansada, ela finalmente disse",
        "K.\n\nMas ninguém respondeu.",
    ]
    r = build_ingest_result(pages, title="t", kind="pdf")
    assert (
        "O interrogatório prosseguiu até que, cansada, ela finalmente disse K."
        in r.text
    )
    assert "Mas ninguém respondeu." in r.text
    assert r.removed == []


def test_paragraph_offsets_reconstruct_exact_text(result):
    for p in result.paragraphs:
        block = result.text[p.start_offset : p.end_offset]
        assert block == block.strip()
        assert "\n" not in block


def test_canonical_text_is_nfc():
    pages = ["CAPÍTULO I\nJosé mora em Brasília."]  # 'é' decomposto (e + ́)
    r = build_ingest_result(pages, title="t", kind="txt")
    assert "José" in r.text  # forma composta NFC
    assert len("José") == 4


# ── capítulos e parágrafos ────────────────────────────────────────────────────


def test_chapters_detected(result):
    assert result.quality.chapters_detected == 2
    assert [c.title for c in result.chapters] == ["Capítulo I", "Capítulo II"]


def test_chapter_spans_cover_text(result):
    first, second = result.chapters
    assert first.end_offset == second.start_offset
    assert second.end_offset == len(result.text)
    heading = result.text[first.start_offset : first.start_offset + len(first.title)]
    assert heading == first.title


def test_paragraph_numbering_resets_per_chapter(result):
    by_loc = {(p.chapter, p.number): p for p in result.paragraphs}
    assert by_loc[(None, 1)].kind is ParagraphKind.texto  # preâmbulo
    assert by_loc[(1, 0)].kind is ParagraphKind.titulo
    assert (1, 1) in by_loc and (1, 2) in by_loc
    assert by_loc[(2, 0)].kind is ParagraphKind.titulo
    assert (2, 1) in by_loc and (2, 2) in by_loc


def test_paragraphs_carry_id_and_source_id(result):
    assert all(len(p.id) == 36 for p in result.paragraphs)
    assert all(p.source_id == result.source.id for p in result.paragraphs)


def test_located_paragraph_contains_quote(result):
    """Critério do B04: o parágrafo devolvido contém o trecho citado."""
    quote = "A senhora Grubach observava da porta."
    offset = result.text.index(quote)
    p = result.paragraph_at(offset)
    assert quote in result.text[p.start_offset : p.end_offset]
    assert result.locate(offset) == "cap. 1, § 1"


def test_roman_numeral_heading_detected():
    r = build_ingest_result(["II\nUm texto qualquer."], title="t", kind="txt")
    assert r.quality.chapters_detected == 1
    assert r.chapters[0].title == "II"


def test_spaced_letters_heading_detected():
    """"C A P Í T U L O I" é título explícito mesmo com letras espaçadas."""
    pages = ["C A P Í T U L O I\nJosef K. compareceu ao local."]
    r = build_ingest_result(pages, title="t", kind="pdf")
    assert r.quality.chapters_detected == 1
    assert r.locate(r.text.index("Josef K. compareceu")) == "cap. 1, § 1"


def test_explicit_headings_take_precedence_over_uppercase():
    """Folha de rosto e subtítulos em maiúsculas não numeram capítulos
    quando a obra tem títulos explícitos; a numeração começa na obra."""
    pages = [
        "O PROCESSO\nFranz Kafka, 1925.",
        "Capítulo I\nA INVESTIGAÇÃO\nJosef K. compareceu ao local.",
        "Capítulo II\nO texto segue adiante.",
    ]
    r = build_ingest_result(pages, title="t", kind="pdf")
    assert r.quality.chapters_detected == 2
    assert [c.title for c in r.chapters] == ["Capítulo I", "Capítulo II"]
    # folha de rosto fica no preâmbulo; subtítulo vira texto do capítulo 1
    assert r.locate(r.text.index("O PROCESSO")) == "§ 1"
    assert r.locate(r.text.index("A INVESTIGAÇÃO")) == "cap. 1, § 1"
    assert r.locate(r.text.index("Josef K. compareceu")) == "cap. 1, § 2"
    assert sum(
        "título em maiúsculas não numerado" in a for a in r.quality.alerts
    ) == 2


def test_uppercase_headings_number_chapters_when_no_explicit():
    """Sem títulos explícitos, a regra de maiúsculas numera — com alerta."""
    pages = ["A PARTIDA\nUm texto.\n\nA CHEGADA\nOutro texto."]
    r = build_ingest_result(pages, title="t", kind="txt")
    assert r.quality.chapters_detected == 2
    assert any("apenas pela regra de maiúsculas" in a for a in r.quality.alerts)


def test_alert_for_empty_chapter():
    pages = ["Capítulo I\nTem texto aqui.\n\nCapítulo II\n\nCapítulo III\nMais texto."]
    r = build_ingest_result(pages, title="t", kind="txt")
    assert "capítulo 2 sem parágrafos de texto" in r.quality.alerts


# ── locate ────────────────────────────────────────────────────────────────────


def test_locate_preamble(result):
    offset = result.text.index("Documento interno")
    assert result.locate(offset) == "§ 1"


def test_locate_chapter_title(result):
    offset = result.text.index("Capítulo I")
    assert result.locate(offset) == "cap. 1, título"


def test_locate_paragraphs(result):
    assert result.locate(result.text.index("Josef K. aguardava")) == "cap. 1, § 1"
    assert result.locate(result.text.index("K. esperou sentado")) == "cap. 1, § 2"
    assert result.locate(result.text.index("K. recebeu aviso")) == "cap. 2, § 1"
    assert result.locate(result.text.index("O interrogatório começou")) == "cap. 2, § 2"


def test_locate_out_of_range_raises(result):
    with pytest.raises(ValueError):
        result.locate(-1)
    with pytest.raises(ValueError):
        result.locate(len(result.text))


# ── QualityReport ─────────────────────────────────────────────────────────────


def test_quality_counts(result):
    q = result.quality
    assert q.pages == 4
    assert q.paragraphs == len(result.paragraphs) == 7
    assert q.removed_by_reason == {"cabecalho": 4, "numero_pagina": 4}
    assert q.alerts == []


def test_alert_when_no_chapters():
    r = build_ingest_result(
        ["só um parágrafo sem capítulo."], title="t", kind="txt"
    )
    assert "nenhum capítulo detectado" in r.quality.alerts


def test_alert_for_empty_page():
    pages = ["um texto.", "", "outro texto.", "mais texto."]
    r = build_ingest_result(pages, title="t", kind="txt")
    assert "página 2 sem texto" in r.quality.alerts
    assert any(i.reason is RemovalReason.pagina_vazia for i in r.removed)


# ── relatório de revisão ──────────────────────────────────────────────────────


def test_render_report_sections(result):
    report = render_report(result)
    assert "cap. 1 — Capítulo I" in report
    assert "Josef K. aguardava" in report  # first line of chapter
    assert "## Itens removidos por página" in report
    assert "cabecalho: O Processo — Franz Kafka" in report
    assert "## Alertas" in report


def test_write_processed_creates_artifacts(result, tmp_path):
    out = write_processed(result, tmp_path / "doc")
    assert out == tmp_path / "doc"
    assert (out / "canonical.txt").read_text(encoding="utf-8") == result.text
    assert (out / "report.md").exists()
    ingest_json = (out / "ingest.json").read_text(encoding="utf-8")
    assert '"contentHash"' in ingest_json
    assert result.text not in ingest_json  # texto fica só em canonical.txt


# ── contrato ──────────────────────────────────────────────────────────────────


def test_pdf_parser_satisfies_document_parser():
    assert isinstance(PdfParser(), DocumentParser)

"""Comparação pdf_loader × Docling com JSON sintético do DoclingDocument."""

from map_relations.ingest.canonical import build_ingest_result
from map_relations.ingest.docling_compare import compare

PAGES = [
    "O PROCESSO\nFranz Kafka, 1925.",
    "Capítulo I\nJosef K. entrou na sala.",
]

DOCLING_DOC = {
    "texts": [
        {"label": "title", "text": "O PROCESSO", "prov": [{"page_no": 1}]},
        {"label": "text", "text": "Franz Kafka, 1925.", "prov": [{"page_no": 1}]},
        {"label": "section_header", "text": "Capítulo I", "prov": [{"page_no": 2}]},
        {
            "label": "section_header",
            "text": "Prisão. Conversa com Grubach",
            "prov": [{"page_no": 2}],
        },
        {"label": "text", "text": "Josef K. entrou na sala.", "prov": [{"page_no": 2}]},
        {
            "label": "text",
            "text": "Parágrafo que atravessa a página.",
            "prov": [{"page_no": 2}, {"page_no": 3}],
        },
        {"label": "page_header", "text": "O Processo — Franz Kafka", "prov": [{"page_no": 2}]},
    ]
}


def _report() -> str:
    result = build_ingest_result(PAGES, title="t", kind="pdf")
    return compare(result, DOCLING_DOC)


def test_report_has_all_sections():
    report = _report()
    for section in [
        "## Títulos explícitos (Docling)",
        "## Subtítulos e seções (Docling, não explícitos)",
        "## Folha de rosto / sumário (antes do primeiro capítulo)",
        "## Cabeçalhos/rodapés restantes no texto canônico",
        "## Parágrafos que atravessam página (Docling)",
        "## Alertas do pdf_loader",
    ]:
        assert section in report


def test_explicit_header_matches_chapter():
    report = _report()
    assert '"Capítulo I" — ✓ casa com capítulo do pdf_loader' in report


def test_subtitle_listed_as_non_explicit():
    assert "Prisão. Conversa com Grubach" in _report()


def test_front_matter_detected_before_first_chapter():
    report = _report()
    assert "p.1 [title]: \"O PROCESSO\"" in report


def test_crossing_paragraph_reported():
    report = _report()
    assert "Parágrafos que atravessam página" in report
    assert "p.2–3" in report


def test_header_not_in_canonical_reported_clean():
    # o cabeçalho sintético não está no canônico (só 2 páginas, sem repetição)
    assert "nenhum — a remoção por repetição cobriu" in _report()

"""Comparação pdf_loader × conversor registrado, sobre LayoutItem[] (B04d
fase 6: generalizado para qualquer conversor, não só Docling — aqui com
JSON sintético do DoclingDocument, traduzido por `docling_items`)."""

from map_relations.ingest.canonical import build_ingest_result
from map_relations.ingest.convert_docling import docling_items
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
        {"label": "page_header", "text": "O Processo — Franz Kafka", "prov": [{"page_no": 2}]},
    ]
}


def _report() -> str:
    result = build_ingest_result(PAGES, title="t", kind="pdf")
    items, _alerts, _pages = docling_items(DOCLING_DOC)
    return compare(result, items)


def test_report_has_all_sections():
    report = _report()
    for section in [
        "## Títulos explícitos (Docling)",
        "## Subtítulos e seções (Docling, não explícitos)",
        "## Folha de rosto / sumário (antes do primeiro capítulo)",
        "## Cabeçalhos/rodapés restantes no texto canônico",
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
    assert "p.1 [titulo]: \"O PROCESSO\"" in report


def test_header_not_in_canonical_reported_clean():
    # o cabeçalho sintético não está no canônico (só 2 páginas, sem repetição)
    assert "nenhum — a remoção por repetição cobriu" in _report()


def test_converter_label_is_parameterized():
    result = build_ingest_result(PAGES, title="t", kind="pdf")
    items, _alerts, _pages = docling_items(DOCLING_DOC)
    report = compare(result, items, converter="MinerU")
    assert "# Comparação MinerU × pdf_loader" in report
    assert "## Títulos explícitos (MinerU)" in report

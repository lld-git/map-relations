"""
Adaptado de src/ingestion/pdf_loader.py do projeto Grafo.
Agora implementa o contrato DocumentParser: retorna IngestResult com texto
canônico NFC, parágrafos, capítulos, itens removidos e QualityReport (B04).
"""

from pathlib import Path

from pypdf import PdfReader

from map_relations.core.ingest_contract import IngestResult

from .canonical import build_ingest_result


def extract_pages(path: str | Path) -> list[str]:
    """Texto bruto de cada página do PDF (entrada da rota pdf_loader)."""
    reader = PdfReader(Path(path))
    return [page.extract_text() or "" for page in reader.pages]


def load_pdf(path: str | Path) -> IngestResult:
    """Extrai texto de um PDF e monta o IngestResult.

    Offsets de segmentos e menções referenciam result.text (canônico NFC);
    result.locate(offset) converte em "cap. X, § Y".
    """
    path = Path(path)
    return build_ingest_result(extract_pages(path), title=path.stem, kind="pdf")


class PdfParser:
    """Implementação de DocumentParser baseada em pypdf."""

    def parse(self, path: Path) -> IngestResult:
        return load_pdf(path)

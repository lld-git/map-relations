"""
Adaptado de src/ingestion/pdf_loader.py do projeto Grafo.
Mudanças: retorna (Source, str) em vez de Document; preserva quebras de parágrafo
para segmentação posterior; calcula content_hash dos bytes brutos.
"""

import re
from pathlib import Path

from pypdf import PdfReader

from .document import Source, compute_hash


def _normalize_text(text: str) -> str:
    text = re.sub(r"-\n", "", text)         # junta palavras hifenizadas no fim da linha
    text = re.sub(r"[^\S\n]+", " ", text)   # colapsa espaços dentro da linha, preserva \n
    text = re.sub(r"\n{3,}", "\n\n", text)  # normaliza múltiplas linhas em branco
    return text.strip()


def load_pdf(path: str | Path) -> tuple[Source, str]:
    """Extrai texto de um PDF com quebras de parágrafo preservadas.

    Retorna (Source, text) onde os offsets de caractere em text são estáveis
    — segmentos e menções referenciam posições nesse string.
    """
    path = Path(path)
    raw_bytes = path.read_bytes()
    reader = PdfReader(path)

    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")

    raw_text = "\n\n".join(pages)
    text = _normalize_text(raw_text)

    source = Source(
        title=path.stem,
        kind="pdf",
        content_hash=compute_hash(raw_bytes),
    )
    return source, text

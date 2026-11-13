"""
Adaptado de src/ingestion/url_loader.py do projeto Grafo.
Mudanças: retorna (Source, str); calcula content_hash do texto extraído normalizado.
"""

import trafilatura

from research.map_relations.core.ids import nfc

from .document import Source, compute_text_hash


def load_url(url: str) -> tuple[Source, str]:
    """Baixa uma URL e extrai o texto principal.

    Retorna (Source, text). Lança ValueError se a página não puder ser baixada.
    """
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        raise ValueError(f"Não foi possível baixar: {url}")

    metadata = trafilatura.extract_metadata(downloaded)
    # offsets contam code points sobre texto NFC (ADR 004)
    text = nfc(trafilatura.extract(downloaded) or "")
    title = metadata.title if metadata and metadata.title else url

    source = Source(
        title=title,
        kind="url",
        content_hash=compute_text_hash(text),
    )
    return source, text

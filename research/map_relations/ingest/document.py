import hashlib

from map_relations.core.ids import nfc
from map_relations.core.models import Source

__all__ = ["Source", "compute_text_hash"]


def compute_text_hash(text: str) -> str:
    """sha256 do texto NFC (UTF-8). Garante que offsets de menções e
    hashes de fonte usem a mesma representação do conteúdo (ADR 004)."""
    return hashlib.sha256(nfc(text).encode("utf-8")).hexdigest()

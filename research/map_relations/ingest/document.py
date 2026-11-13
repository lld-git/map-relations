import hashlib
import uuid
from datetime import date

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def compute_text_hash(text: str) -> str:
    """sha256 do texto normalizado (UTF-8). Garante que offsets de menções e
    hashes de fonte usem a mesma representação do conteúdo."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Source(BaseModel):
    """Representa um documento ingerido (PDF, URL, TXT, EPUB)."""

    id: str = Field(default_factory=_new_id)
    title: str
    kind: str  # "pdf" | "url" | "txt" | "epub"
    published_at: date | None = None
    content_hash: str  # sha256 do texto normalizado; offsets de menções referenciam esse mesmo texto

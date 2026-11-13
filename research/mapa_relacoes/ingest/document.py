import hashlib
import uuid
from datetime import date

from pydantic import BaseModel, Field


def _new_id() -> str:
    return str(uuid.uuid4())


def compute_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class Source(BaseModel):
    """Representa um documento ingerido (PDF, URL, TXT, EPUB)."""

    id: str = Field(default_factory=_new_id)
    title: str
    kind: str  # "pdf" | "url" | "txt" | "epub"
    published_at: date | None = None
    content_hash: str  # sha256 dos bytes originais; vincula reprocessamentos ao mesmo arquivo

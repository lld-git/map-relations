"""Contrato de ingestão: todo parser (pdf_loader, TXT, EPUB, Docling) produz
um IngestResult sobre texto canônico NFC. Offsets em code points (ADR 004)."""

from __future__ import annotations

import bisect
import enum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from map_relations.core.ids import new_id
from map_relations.core.models import Source


class _Base(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ParagraphKind(enum.StrEnum):
    titulo = "titulo"
    subtitulo = "subtitulo"
    texto = "texto"


class RemovalReason(enum.StrEnum):
    cabecalho = "cabecalho"
    rodape = "rodape"
    numero_pagina = "numero_pagina"
    pagina_vazia = "pagina_vazia"


class Paragraph(_Base):
    """Bloco do texto canônico, separado por linha em branco.
    number reinicia em 1 a cada capítulo (0 = título do capítulo);
    no preâmbulo, antes do primeiro capítulo, conta globalmente."""

    id: str = Field(default_factory=new_id)
    source_id: str
    chapter: int | None = None  # 1-based; None = preâmbulo
    number: int  # 1-based dentro do capítulo; 0 = título/subtítulo
    kind: ParagraphKind = ParagraphKind.texto
    page: int | None = None  # página de origem (via <!-- p.N -->), se houver
    start_offset: int
    end_offset: int


class ChapterSpan(_Base):
    index: int  # 1-based
    title: str
    start_offset: int
    end_offset: int


class RemovedItem(_Base):
    page: int  # 1-based
    reason: RemovalReason
    text: str


class QualityReport(_Base):
    pages: int
    chapters_detected: int
    paragraphs: int
    removed_by_reason: dict[str, int]
    alerts: list[str]


class IngestResult(_Base):
    source: Source
    text: str  # canônico NFC; todo offset do projeto referencia este string
    paragraphs: list[Paragraph]
    chapters: list[ChapterSpan]
    removed: list[RemovedItem]
    quality: QualityReport

    def paragraph_at(self, offset: int) -> Paragraph:
        """Parágrafo que contém o offset. Offset fora do texto lança ValueError."""
        if not 0 <= offset < len(self.text):
            raise ValueError(f"offset {offset} fora do texto [0, {len(self.text)})")
        starts = [p.start_offset for p in self.paragraphs]
        i = bisect.bisect_right(starts, offset) - 1
        if i < 0:
            raise ValueError(f"offset {offset} antes do primeiro parágrafo")
        return self.paragraphs[i]

    def locate(self, offset: int) -> str:
        """Converte um offset do texto canônico em "cap. X, § Y".

        No preâmbulo (antes do primeiro capítulo) retorna "§ Y".
        No título de um capítulo retorna "cap. X, título".
        Referência legível apenas: nunca é usada para verificar provas —
        a verificação usa sempre os offsets sobre o texto canônico.
        """
        p = self.paragraph_at(offset)
        if p.chapter is None:
            return f"§ {p.number}"
        if p.kind is ParagraphKind.titulo:
            return f"cap. {p.chapter}, título"
        if p.kind is ParagraphKind.subtitulo:
            return f"cap. {p.chapter}, subtítulo"
        return f"cap. {p.chapter}, § {p.number}"

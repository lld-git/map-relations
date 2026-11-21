from __future__ import annotations

import hashlib
import unicodedata
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # models importa ids; só tipagem aqui evita o ciclo
    from map_relations.core.models import RelationType


def new_id() -> str:
    return str(uuid.uuid4())


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def claim_key(
    subject_id: str,
    relation_type: RelationType,
    object_id: str,
    *,
    asserted_by: str | None = None,
    narrative_scope: str | None = None,
) -> str:
    """Chave de conteúdo da claim (ADR 003, ADR 011).

    A simetria vem do RelationType. `asserted_by` e `narrative_scope` entram
    no hash só quando não são None, então a chave de uma claim comum continua
    hash(s, type_id, o). A classe fica fora da chave.
    """
    s, o = subject_id, object_id
    if relation_type.symmetric:
        s, o = sorted([s, o])
    parts = [s, relation_type.id, o]
    if asserted_by is not None:
        parts += ["asserted_by", asserted_by]
    if narrative_scope is not None:
        parts += ["narrative_scope", narrative_scope]
    return _hash(*parts)


def participation_key(event_id: str, entity_id: str, role: str) -> str:
    return _hash(event_id, entity_id, role)


def evidence_key(source_content_hash: str, start: int, end: int) -> str:
    return _hash(source_content_hash, str(start), str(end))

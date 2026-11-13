import hashlib
import unicodedata
import uuid


def new_id() -> str:
    return str(uuid.uuid4())


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _hash(*parts: str) -> str:
    return hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def claim_key(subject_id: str, type_id: str, object_id: str) -> str:
    return _hash(subject_id, type_id, object_id)


def participation_key(event_id: str, entity_id: str, role: str) -> str:
    return _hash(event_id, entity_id, role)


def evidence_key(source_content_hash: str, start: int, end: int) -> str:
    return _hash(source_content_hash, str(start), str(end))

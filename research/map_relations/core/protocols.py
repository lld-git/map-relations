"""Contratos de dependências externas (Princípio 2 do CLAUDE.md).

Apenas LlmEngine.complete é assíncrono; o restante do domínio é síncrono.
A camada de tarefa orquestra chamadas com gather e semáforo (ADR 005).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from research.map_relations.core.models import Source


class _Base(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ── LlmEngine ─────────────────────────────────────────────────────────────────


class LlmCapabilities(_Base):
    json_schema: bool
    max_context_tokens: int
    runs_locally: bool
    data_policy_note: str


class LlmMessage(_Base):
    role: str  # system | user | assistant
    content: str


class LlmRequest(_Base):
    messages: list[LlmMessage]
    json_schema: dict[str, Any] | None = None
    max_output_tokens: int
    temperature: float
    metadata: dict[str, str] = {}


class LlmUsage(_Base):
    input_tokens: int
    output_tokens: int


class LlmResponse(_Base):
    text: str
    parsed_json: dict[str, Any] | None = None
    usage: LlmUsage | None = None
    finish_reason: str
    raw: Any = None


class LlmError(Exception):
    pass


class RateLimited(LlmError):
    def __init__(self, message: str = "", retry_at: datetime | None = None) -> None:
        self.retry_at = retry_at
        super().__init__(message)


class InvalidResponse(LlmError):
    pass


class AuthError(LlmError):
    pass


class NetworkError(LlmError):
    pass


class Aborted(LlmError):
    pass


@runtime_checkable
class LlmEngine(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def capabilities(self) -> LlmCapabilities: ...

    async def complete(self, req: LlmRequest) -> LlmResponse: ...


# ── ingestão e persistência ───────────────────────────────────────────────────


@runtime_checkable
class SourceConnector(Protocol):
    """Localiza documentos de uma origem (pasta local, URL etc.)."""

    def list_documents(self) -> list[str]: ...

    def fetch(self, ref: str) -> bytes: ...


@runtime_checkable
class DocumentParser(Protocol):
    """Converte um documento bruto em (Source, texto NFC normalizado)."""

    def parse(self, path: Path) -> tuple[Source, str]: ...


@runtime_checkable
class ProjectStore(Protocol):
    """Persistência de artefatos do projeto. Implementações entram em blocos futuros."""

    def save(self, kind: str, item: BaseModel) -> None: ...

    def get(self, kind: str, item_id: str) -> BaseModel | None: ...

    def list(self, kind: str) -> list[BaseModel]: ...

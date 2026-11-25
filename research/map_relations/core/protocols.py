"""Contratos de dependências externas (Princípio 2 do CLAUDE.md).

Apenas LlmEngine.complete é assíncrono; o restante do domínio é síncrono.
A camada de tarefa orquestra chamadas com gather e semáforo (ADR 005).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from map_relations.core.ingest_contract import IngestResult


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
    """Converte um documento bruto num IngestResult (texto canônico NFC,
    parágrafos, capítulos, itens removidos e QualityReport)."""

    def parse(self, path: Path) -> IngestResult: ...


@runtime_checkable
class ProjectStore(Protocol):
    """Persistência de artefatos do projeto. Implementações entram em blocos futuros."""

    def save(self, kind: str, item: BaseModel) -> None: ...

    def get(self, kind: str, item_id: str) -> BaseModel | None: ...

    def list(self, kind: str) -> list[BaseModel]: ...


# ── RunTracker (B02 §8) ───────────────────────────────────────────────────────

LOCAL_TRACKING_HOSTS = frozenset({"mlflow", "localhost", "127.0.0.1"})
_LOCAL_SCHEMES = frozenset({"http", "https"})
# palavras sem esquema que o MLflow trata como serviço remoto (Databricks)
_RESERVED_REMOTE_WORDS = frozenset({"databricks", "databricks-uc", "uc"})


class RemoteTrackingRefused(ValueError):
    """O endereço do rastreador está fora da máquina (princípio 6)."""


def check_local_tracking_uri(uri: str) -> str:
    """Devolve `uri` se ela fica na máquina; senão levanta RemoteTrackingRefused.

    Aceita: `http(s)://` com host `mlflow` (rede do compose), `localhost` ou
    `127.0.0.1`; e armazenamento em disco (`file:`, `sqlite:` ou caminho local).
    Recusa qualquer outro host ou esquema, inclusive o truque `user@host`:
    quem decide é `urlparse(...).hostname`, não o texto antes da barra.
    """
    if not uri.strip():
        raise RemoteTrackingRefused("endereço do rastreador vazio")
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    if scheme in ("file", "sqlite"):
        if parsed.hostname not in (None, "", "localhost"):
            raise RemoteTrackingRefused(f"{scheme}: com host remoto recusado")
        return uri
    if scheme == "" or (len(scheme) == 1 and ":" in uri[:3]):  # caminho local
        if uri.strip().lower() in _RESERVED_REMOTE_WORDS:
            raise RemoteTrackingRefused(f"'{uri}' aponta para um serviço remoto do MLflow")
        return uri
    if scheme not in _LOCAL_SCHEMES:
        raise RemoteTrackingRefused(f"esquema '{scheme}' recusado (só http, https ou disco)")
    try:
        host = parsed.hostname
    except ValueError as exc:  # colchetes mal formados etc.
        raise RemoteTrackingRefused("endereço do rastreador ilegível") from exc
    if host not in LOCAL_TRACKING_HOSTS:
        raise RemoteTrackingRefused(
            f"host '{host}' fora da máquina; permitidos: {sorted(LOCAL_TRACKING_HOSTS)}"
        )
    return uri


@runtime_checkable
class RunTracker(Protocol):
    """Registro de execuções de avaliação (MLflow é um adaptador, `NullTracker` o padrão).

    Todo adaptador deve chamar `check_local_tracking_uri` no endereço que usa.
    Trechos protegidos da obra só podem ir em `log_artifact`; nunca em parâmetros,
    métricas ou tags.
    """

    def start(self, run_name: str) -> None: ...

    def log_params(self, params: Mapping[str, str | int | float | bool]) -> None: ...

    def log_metrics(self, metrics: Mapping[str, float]) -> None: ...

    def log_artifact(self, path: Path) -> None: ...

    def set_tags(self, tags: Mapping[str, str]) -> None: ...

    def end(self, status: str = "FINISHED") -> None: ...

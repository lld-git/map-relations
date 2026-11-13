from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

from map_relations.core.ids import new_id


class _Base(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# ── enums ─────────────────────────────────────────────────────────────────────


class EntityKind(enum.StrEnum):
    pessoa = "pessoa"
    grupo = "grupo"
    lugar = "lugar"
    objeto = "objeto"
    evento = "evento"


class TargetType(enum.StrEnum):
    claim = "claim"
    participation = "participation"
    entity = "entity"


class ClaimClass(enum.StrEnum):
    afirmada = "afirmada"
    inferida = "inferida"
    coocorrencia = "coocorrencia"
    interpretacao = "interpretacao"


class ClaimState(enum.StrEnum):
    proposta = "proposta"
    verificada = "verificada"
    rejeitada = "rejeitada"
    confirmada_humano = "confirmada_humano"
    rejeitada_humano = "rejeitada_humano"


class Role(enum.StrEnum):
    autor = "autor"
    alvo = "alvo"
    testemunha = "testemunha"
    beneficiario = "beneficiario"
    participante = "participante"


class Actor(enum.StrEnum):
    auto = "auto"
    humano = "humano"


class ChangeAction(enum.StrEnum):
    create = "create"
    update = "update"
    delete = "delete"
    state_change = "state_change"


class RunStatus(enum.StrEnum):
    running = "running"
    done = "done"
    failed = "failed"
    aborted = "aborted"


class LensScope(enum.StrEnum):
    document = "document"
    chapter = "chapter"
    segment = "segment"


class LensRetrieval(enum.StrEnum):
    full = "full"
    windowed = "windowed"
    semantic = "semantic"


class LensEvidenceRule(enum.StrEnum):
    required = "required"
    optional = "optional"
    forbidden = "forbidden"


class PassStopReason(enum.StrEnum):
    max_calls = "max_calls"
    no_new_claims = "no_new_claims"
    error = "error"
    completed = "completed"


class NoteKind(enum.StrEnum):
    comment = "comment"
    correction = "correction"
    question = "question"
    observation = "observation"


# ── offset mixin ──────────────────────────────────────────────────────────────


class _WithOffsets(_Base):
    start_offset: int
    end_offset: int

    @model_validator(mode="after")
    def _offsets_valid(self) -> _WithOffsets:
        if self.start_offset < 0 or self.end_offset < 0:
            raise ValueError("offsets must be >= 0")
        if self.start_offset >= self.end_offset:
            raise ValueError("start_offset must be < end_offset")
        return self


# ── domain models ─────────────────────────────────────────────────────────────


class Source(_Base):
    id: str = Field(default_factory=new_id)
    title: str
    kind: str  # pdf | url | txt | epub
    published_at: date | None = None
    content_hash: str


class Entity(_Base):
    id: str = Field(default_factory=new_id)
    project_id: str
    preferred_name: str
    kind: EntityKind
    description: str | None = None


class Alias(_Base):
    id: str = Field(default_factory=new_id)
    entity_id: str
    name: str
    source: str
    confidence: float

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {v}")
        return v


class Segment(_WithOffsets):
    id: str = Field(default_factory=new_id)
    source_id: str
    chapter: str | None = None
    text: str


class Mention(_WithOffsets):
    id: str = Field(default_factory=new_id)
    entity_id: str
    segment_id: str
    surface: str


class RelationType(_Base):
    id: str = Field(default_factory=new_id)
    label: str
    definition: str
    subject_kinds: list[EntityKind]
    object_kinds: list[EntityKind]
    version: int


class Claim(_Base):
    id: str = Field(default_factory=new_id)
    claim_key: str
    subject_id: str
    type_id: str
    object_id: str
    # 'class' is a Python keyword; explicit alias keeps JSON key as "class"
    claim_class: ClaimClass = Field(alias="class")
    state: ClaimState = ClaimState.proposta
    confidence: float
    pass_id: str

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {v}")
        return v


class Participation(_Base):
    id: str = Field(default_factory=new_id)
    participation_key: str
    event_id: str
    entity_id: str
    role: Role
    state: ClaimState = ClaimState.proposta
    confidence: float
    pass_id: str

    @field_validator("confidence")
    @classmethod
    def _confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {v}")
        return v


class Evidence(_WithOffsets):
    id: str = Field(default_factory=new_id)
    evidence_key: str
    target_type: TargetType
    target_id: str
    source_id: str
    quote: str


class TimeScope(_Base):
    target_type: TargetType
    target_id: str
    story_time: str | None = None
    story_order: int | None = None
    published_at: date | None = None
    chapter: str | None = None
    duration: str | None = None


class Lens(_Base):
    id: str = Field(default_factory=new_id)
    version: int
    question: str
    relation_types: list[str]
    scope: LensScope
    retrieval: LensRetrieval
    evidence_rule: LensEvidenceRule
    max_calls: int


class Pass(_Base):
    id: str = Field(default_factory=new_id)
    level: int
    lens_id: str | None = None
    target: str
    calls: int
    proposed: int
    verified: int
    stop_reason: PassStopReason

    @field_validator("level")
    @classmethod
    def _level_range(cls, v: int) -> int:
        if not 0 <= v <= 5:
            raise ValueError(f"level must be in [0, 5], got {v}")
        return v


class Run(_Base):
    id: str = Field(default_factory=new_id)
    task: str
    engine: str
    model: str
    prompt_version: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    status: RunStatus


class ChangeLog(_Base):
    id: str = Field(default_factory=new_id)
    action: ChangeAction
    actor: Actor
    target_type: TargetType
    target_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    run_id: str | None = None
    pass_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Note(_Base):
    id: str = Field(default_factory=new_id)
    target_type: TargetType
    target_id: str
    kind: NoteKind
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

"""Formato de execução avaliado pelo `eval` (B02 §7).

É o que o B03 passa a emitir. No B02 só existe em fixtures sintéticas.
Sujeito, objeto e `asserted_by` vêm por nome: o avaliador os liga às entidades
do gabarito (nome ou alias normalizado). Nada aqui é gravado no gabarito.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from map_relations.core.models import ClaimClass, NarrativeScope

RUN_SCHEMA_VERSION = 1


class _Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class RunMeta(_Model):
    """Princípio 10: o que produziu o resultado."""

    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)
    level: str | None = None
    lens: str | None = None


class RunEntity(_Model):
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)


class RunEvidence(_Model):
    quote: str = Field(min_length=1)
    start_offset: int = Field(alias="startOffset", ge=0)
    end_offset: int = Field(alias="endOffset", ge=1)


class RunClaim(_Model):
    subject: str
    type_: str = Field(alias="type")
    object_: str = Field(alias="object")
    class_: ClaimClass = Field(alias="class")
    asserted_by: str | None = None
    narrative_scope: NarrativeScope = NarrativeScope.obra
    level: str | None = None  # sobrepõe `meta.level` nesta claim
    lens: str | None = None
    evidence: list[RunEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def _asserted_by_iff_alegada(self) -> RunClaim:
        alegada = self.class_ is ClaimClass.alegada
        if alegada and not self.asserted_by:
            raise ValueError("class = alegada exige asserted_by")
        if not alegada and self.asserted_by is not None:
            raise ValueError("asserted_by só é permitido com class = alegada")
        return self


class RunCall(_Model):
    json_valid: bool


class RunFile(_Model):
    schema_version: Literal[1]
    # vira nome de pasta em eval/reports/: sem separador de caminho
    run_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    meta: RunMeta
    entities: list[RunEntity] = Field(default_factory=list)
    claims: list[RunClaim] = Field(default_factory=list)
    calls: list[RunCall] = Field(default_factory=list)


def load_run(path: Path) -> RunFile:
    """Lê e valida a estrutura (princípio 3). Levanta ValidationError."""
    return RunFile.model_validate(json.loads(path.read_text(encoding="utf-8")))

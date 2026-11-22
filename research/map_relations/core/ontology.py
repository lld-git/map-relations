"""Ontologia de relações (B02a, ADR 011): modelos do formato, validação e consultas.

Módulo puro, sem I/O: `build_ontology(dados)` recebe o conteúdo já lido do YAML.
A validação junta todos os erros e levanta um único OntologyError.
"""

from __future__ import annotations

import enum
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from map_relations.core.models import Claim, EntityKind, RelationType

ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_WIKIDATA = re.compile(r"^P\d+$")
_LOWER_CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*$")


class OntologyError(ValueError):
    """Ontologia inválida; `errors` tem uma linha por problema."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


class OntologyLookupError(KeyError):
    """Id desconhecido numa consulta."""


class AbstractTypeError(ValueError):
    """Tipo abstrato usado onde só cabe tipo anotável."""


class Status(enum.StrEnum):
    active = "active"
    obsolete = "obsolete"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InverseDef(_Strict):
    id: str
    label: str


class Mappings(_Strict):
    wikidata: str | None = None
    schema_org: str | None = None
    foaf: str | None = None


class AbstractTypeDef(_Strict):
    id: str
    label: str
    definition: str
    domain: list[EntityKind]
    range: list[EntityKind]
    status: Status = Status.active
    replaced_by: list[str] = Field(default_factory=list)
    # só existe para o validador apontar o erro com mensagem própria
    parent: str | None = None


class TypeDef(_Strict):
    id: str
    version: int = Field(ge=1)
    status: Status = Status.active
    replaced_by: list[str] = Field(default_factory=list)
    label: str
    definition: str
    when_to_use: str
    when_not_to_use: str
    example: str
    parent: str | None = None  # obrigatório; conferido pelo validador
    domain: list[EntityKind]
    range: list[EntityKind]
    symmetric: bool
    inverse_of: InverseDef | None = None
    irreflexive: bool
    disjoint_with: list[str] = Field(default_factory=list)
    disjoint_note: str | None = None
    mappings: Mappings = Field(default_factory=Mappings)
    mappings_note: str | None = None


class OntologyFile(_Strict):
    version: int = Field(ge=1)
    abstract_types: list[AbstractTypeDef]
    types: list[TypeDef]


@dataclass(frozen=True)
class Conflict:
    """Duas claims de tipos disjuntos sobre o mesmo par não ordenado."""

    claim_a: Claim
    claim_b: Claim


# ── validação ────────────────────────────────────────────────────────────────


def _label(section: str, raw: Any, index: int) -> str:
    if isinstance(raw, Mapping) and isinstance(raw.get("id"), str):
        return f"{section}[{raw['id']}]"
    return f"{section}[{index}]"


def _pydantic_lines(exc: ValidationError, data: Mapping[str, Any]) -> list[str]:
    lines = []
    for err in exc.errors():
        loc = list(err["loc"])
        parts: list[str] = []
        node: Any = data
        i = 0
        while i < len(loc):
            key = loc[i]
            if isinstance(key, int):
                parts.append(f"[{key}]")
                node = node[key] if isinstance(node, list) and key < len(node) else None
            elif (
                key in ("types", "abstract_types")
                and i + 1 < len(loc)
                and isinstance(loc[i + 1], int)
            ):
                raw_list = node.get(key) if isinstance(node, Mapping) else None
                idx = int(loc[i + 1])
                raw = raw_list[idx] if isinstance(raw_list, list) and idx < len(raw_list) else None
                parts.append(("." if parts else "") + _label(str(key), raw, idx))
                node = raw
                i += 1
            else:
                parts.append(("." if parts else "") + str(key))
                node = node.get(key) if isinstance(node, Mapping) else None
            i += 1
        lines.append(f"{''.join(parts) or '<raiz>'}: {err['msg']}")
    return lines


def check_parent_chain(parents: Mapping[str, str | None]) -> list[str]:
    """Defesa: ciclo na cadeia de pais e profundidade maior que 2 (tipo -> abstrato)."""
    errors = []
    for start in parents:
        seen = [start]
        cur = parents.get(start)
        while cur is not None:
            if cur in seen:
                errors.append(f"{start}: ciclo na cadeia de pais ({' -> '.join([*seen, cur])})")
                break
            seen.append(cur)
            cur = parents.get(cur)
        else:
            if len(seen) > 2:
                errors.append(
                    f"{start}: profundidade {len(seen)} acima do máximo de 2 ({' -> '.join(seen)})"
                )
    return errors


def _validate(f: OntologyFile) -> list[str]:
    errs: list[str] = []
    abstract = {a.id: a for a in f.abstract_types}
    annot = {t.id: t for t in f.types}

    # espaço único de ids
    owners: dict[str, list[str]] = defaultdict(list)
    for a in f.abstract_types:
        owners[a.id].append(f"abstract_types[{a.id}]")
    for t in f.types:
        owners[t.id].append(f"types[{t.id}]")
        if t.inverse_of is not None:
            owners[t.inverse_of.id].append(f"types[{t.id}].inverse_of")
    for id_, where in owners.items():
        if not ID_PATTERN.match(id_):
            errs.append(f"{where[0]}: id '{id_}' fora do formato {ID_PATTERN.pattern}")
        if len(where) > 1:
            errs.append(f"{where[0]}: id '{id_}' duplicado ({', '.join(where)})")

    def kinds_within(child: Iterable[EntityKind], parent: Iterable[EntityKind]) -> bool:
        return set(child) <= set(parent)

    for a in f.abstract_types:
        w = f"abstract_types[{a.id}]"
        if a.parent is not None:
            errs.append(f"{w}.parent: tipo abstrato não tem parent")
        if not a.domain:
            errs.append(f"{w}.domain: não pode ser vazio")
        if not a.range:
            errs.append(f"{w}.range: não pode ser vazio")
        errs += _obsolete_errors(w, a.status, a.replaced_by, a.id, abstract)

    for t in f.types:
        w = f"types[{t.id}]"
        if t.parent is None:
            errs.append(f"{w}.parent: obrigatório em tipo anotável")
        elif t.parent in annot:
            errs.append(f"{w}.parent: '{t.parent}' é tipo anotável; o pai deve ser abstrato")
        elif t.parent not in abstract:
            errs.append(f"{w}.parent: '{t.parent}' não existe")
        else:
            p = abstract[t.parent]
            if p.status is not Status.active:
                errs.append(f"{w}.parent: '{t.parent}' está obsoleto")
            if not kinds_within(t.domain, p.domain):
                errs.append(f"{w}.domain: fora do domain do pai '{t.parent}'")
            if not kinds_within(t.range, p.range):
                errs.append(f"{w}.range: fora do range do pai '{t.parent}'")
        if not t.domain:
            errs.append(f"{w}.domain: não pode ser vazio")
        if not t.range:
            errs.append(f"{w}.range: não pode ser vazio")

        if t.symmetric and t.inverse_of is not None:
            errs.append(f"{w}.inverse_of: tipo simétrico não tem inverse_of")
        if not t.symmetric and t.inverse_of is None:
            errs.append(f"{w}.inverse_of: obrigatório em tipo assimétrico")

        for target in t.disjoint_with:
            if target == t.id:
                errs.append(f"{w}.disjoint_with: '{target}' é o próprio tipo")
            elif target in abstract:
                errs.append(f"{w}.disjoint_with: '{target}' é tipo abstrato")
            elif target not in annot:
                errs.append(f"{w}.disjoint_with: '{target}' não existe")
            elif t.id not in annot[target].disjoint_with:
                errs.append(
                    f"{w}.disjoint_with: '{target}' não é recíproco "
                    f"(falta '{t.id}' em types[{target}].disjoint_with)"
                )

        m = t.mappings
        if m.wikidata is not None and not _WIKIDATA.match(m.wikidata):
            errs.append(f"{w}.mappings.wikidata: '{m.wikidata}' fora do formato P<número>")
        for field in ("schema_org", "foaf"):
            val = getattr(m, field)
            if val is not None and not _LOWER_CAMEL.match(val):
                errs.append(f"{w}.mappings.{field}: '{val}' fora do formato lowerCamel")

        errs += _obsolete_errors(w, t.status, t.replaced_by, t.id, annot)

    errs += [f"parent: {e}" for e in check_parent_chain(_parents(f))]
    return errs


def _parents(f: OntologyFile) -> dict[str, str | None]:
    out: dict[str, str | None] = {a.id: a.parent for a in f.abstract_types}
    out.update({t.id: t.parent for t in f.types})
    return out


def _obsolete_errors(
    where: str,
    status: Status,
    replaced_by: Sequence[str],
    self_id: str,
    same_kind: Mapping[str, Any],
) -> list[str]:
    errs = []
    if status is Status.obsolete:
        if not replaced_by:
            errs.append(f"{where}.replaced_by: obrigatório (não vazio) em tipo obsolete")
        for r in replaced_by:
            if r == self_id or r not in same_kind:
                errs.append(f"{where}.replaced_by: '{r}' não existe")
            elif same_kind[r].status is not Status.active:
                errs.append(f"{where}.replaced_by: '{r}' não está ativo")
    elif replaced_by:
        errs.append(f"{where}.replaced_by: só vale com status obsolete")
    return errs


# ── objeto Ontology ──────────────────────────────────────────────────────────


class Ontology:
    def __init__(self, file: OntologyFile) -> None:
        self.file = file
        self._abstract = {a.id: a for a in file.abstract_types}
        self._types = {t.id: t for t in file.types}
        self._inverse = {t.inverse_of.id: t.id for t in file.types if t.inverse_of is not None}

    @property
    def version(self) -> int:
        return self.file.version

    @property
    def n_annotatable(self) -> int:
        return len(self._types)

    @property
    def n_abstract(self) -> int:
        return len(self._abstract)

    def annotatable(self, *, include_obsolete: bool = False) -> list[TypeDef]:
        return [t for t in self.file.types if include_obsolete or t.status is Status.active]

    def get(self, id_: str) -> TypeDef | AbstractTypeDef:
        if id_ in self._types:
            return self._types[id_]
        if id_ in self._abstract:
            return self._abstract[id_]
        raise OntologyLookupError(id_)

    def canonicalize(self, type_or_inverse_id: str, s: str, o: str) -> tuple[str, str, str]:
        """Normaliza a visão inversa: troca sujeito e objeto e devolve o tipo canônico."""
        if type_or_inverse_id in self._types:
            return type_or_inverse_id, s, o
        if type_or_inverse_id in self._inverse:
            return self._inverse[type_or_inverse_id], o, s
        if type_or_inverse_id in self._abstract:
            raise AbstractTypeError(f"'{type_or_inverse_id}' é tipo abstrato, não anotável")
        raise OntologyLookupError(type_or_inverse_id)

    def ancestors(self, id_: str) -> list[str]:
        """Pais do tipo, do mais próximo ao mais distante ([] para abstrato)."""
        out: list[str] = []
        cur = self.get(id_).parent
        while cur is not None and cur not in out:
            out.append(cur)
            cur = self._abstract[cur].parent if cur in self._abstract else None
        return out

    def family(self, id_: str) -> list[str]:
        """Ids anotáveis que compartilham a raiz abstrata do tipo (inclui o próprio)."""
        root = id_ if id_ in self._abstract else self.ancestors(id_)[-1]
        return [t.id for t in self.file.types if t.parent == root]

    def disjoint_conflicts(self, claims: Iterable[Claim]) -> list[Conflict]:
        """X(A,B) com Y(B,A) ou Y(A,B) quando X e Y são disjuntos (alerta, D5)."""
        by_pair: dict[frozenset[str], list[Claim]] = defaultdict(list)
        for c in claims:
            by_pair[frozenset((c.subject_id, c.object_id))].append(c)
        out: list[Conflict] = []
        for group in by_pair.values():
            for i, a in enumerate(group):
                ta = self._types.get(a.type_id)
                if ta is None:
                    continue
                for b in group[i + 1 :]:
                    if b.type_id in ta.disjoint_with:
                        out.append(Conflict(a, b))
        return out

    def relation_types(self) -> list[RelationType]:
        """RelationType de todos os tipos anotáveis, inclusive obsoletos."""
        return [
            RelationType(
                id=t.id,
                label=t.label,
                definition=t.definition,
                subject_kinds=list(t.domain),
                object_kinds=list(t.range),
                version=t.version,
                symmetric=t.symmetric,
            )
            for t in self.file.types
        ]

    def to_dict(self) -> dict[str, Any]:
        return self.file.model_dump(mode="json")


def build_ontology(data: Mapping[str, Any]) -> Ontology:
    """Valida o conteúdo do YAML; levanta OntologyError com todos os erros."""
    try:
        file = OntologyFile.model_validate(data)
    except ValidationError as exc:
        raise OntologyError(_pydantic_lines(exc, data)) from exc
    errors = _validate(file)
    if errors:
        raise OntologyError(errors)
    return Ontology(file)

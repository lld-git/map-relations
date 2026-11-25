"""Alinhamento e casamento claim × gabarito (B02 §7, D5).

Duas medidas, calculadas de forma independente:
- **estrita**: `claim_key` do ADR 011 (simetria do tipo, `asserted_by` e
  `narrative_scope` na chave; classe fora);
- **relaxada**: a mesma chave sem `asserted_by` (a classe já fica fora).

Cada item do gabarito é usado no máximo uma vez. Depois do acerto exato vem o
acerto no tipo pai, sobre o que sobrou.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from map_relations.core.ids import claim_key
from map_relations.core.models import ClaimClass, NarrativeScope, RelationType
from map_relations.core.ontology import (
    AbstractTypeError,
    Ontology,
    OntologyLookupError,
)
from map_relations.evaluation.gold import GoldRelation, ProofSummary
from map_relations.evaluation.run_file import RunClaim, RunEvidence

Measure = Literal["estrita", "relaxada"]
MEASURES: tuple[Measure, ...] = ("estrita", "relaxada")
UNALIGNED = "~"  # prefixo de id para nome sem casamento: nunca é igual a um id do gabarito
INVALID_TYPE = "(tipo_invalido)"
NO_PARENT = "(sem_pai)"


class EvalInputError(Exception):
    """Gabarito ou execução inutilizável para a avaliação (código de saída 2)."""

    def __init__(self, errors: Sequence[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def normalize_name(name: str) -> str:
    """NFC, sem acentos, casefold, espaços colapsados."""
    nfd = unicodedata.normalize("NFD", unicodedata.normalize("NFC", name))
    bare = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", bare.casefold()).strip()


# ── itens comparáveis ─────────────────────────────────────────────────────────


@dataclass
class Item:
    """Claim da execução ou relação do gabarito, já normalizada."""

    ref: str  # id da relação (gabarito) ou "claim#<n>" (execução)
    subject: str
    type_id: str
    object_: str
    class_: ClaimClass
    asserted_by: str | None
    scope: NarrativeScope
    strict_key: str
    relaxed_key: str
    valid_type: bool = True
    # gabarito
    relation: GoldRelation | None = None
    proof: ProofSummary | None = None
    # execução
    claim: RunClaim | None = None
    evidence: list[RunEvidence] = field(default_factory=list)
    chapters: set[str] = field(default_factory=set)  # capítulos das evidências localizadas
    level: str = "(sem)"
    lens: str = "(sem)"


def make_item(
    ref: str,
    type_raw: str,
    subject: str,
    object_: str,
    class_: ClaimClass,
    asserted_by: str | None,
    scope: NarrativeScope,
    ontology: Ontology,
    types: dict[str, RelationType],
) -> Item:
    try:
        type_id, s, o = ontology.canonicalize(type_raw, subject, object_)
    except (AbstractTypeError, OntologyLookupError):
        bad = f"invalido:{ref}"  # única por item: nunca casa
        return Item(
            ref, subject, INVALID_TYPE, object_, class_, asserted_by, scope, bad, bad, False
        )
    rt = types[type_id]
    strict = claim_key(s, rt, o, asserted_by=asserted_by, narrative_scope=scope.value)
    relaxed = claim_key(s, rt, o, asserted_by=None, narrative_scope=scope.value)
    return Item(ref, s, type_id, o, class_, asserted_by, scope, strict, relaxed)


# ── casamento ─────────────────────────────────────────────────────────────────


@dataclass
class MatchResult:
    exact: list[tuple[Item, Item]] = field(default_factory=list)  # (execução, gabarito)
    parent: list[tuple[Item, Item]] = field(default_factory=list)
    runs_unmatched_exact: list[Item] = field(default_factory=list)  # inclui os acertos no pai
    golds_unmatched_exact: list[Item] = field(default_factory=list)
    runs_unmatched: list[Item] = field(default_factory=list)  # falso positivo de verdade
    golds_unmatched: list[Item] = field(default_factory=list)  # falso negativo de verdade
    # claims que só casam com relação do gabarito SEM prova: nem acerto nem falso positivo
    ignored_unproved: int = 0
    considered: list[Item] = field(default_factory=list)  # execução menos as ignoradas


def match(
    runs: Sequence[Item],
    golds: Sequence[Item],
    measure: Measure,
    ontology: Ontology,
    unproved_keys: frozenset[str] = frozenset(),
) -> MatchResult:
    """`unproved_keys`: chaves relaxadas das relações do gabarito sem prova."""
    used: set[int] = set()  # índices do gabarito já usados
    matched_run: set[int] = set()
    res = MatchResult()

    def run_pass(key_of_run: str, key_of_gold: str) -> None:
        for ri, r in enumerate(runs):
            if ri in matched_run or not r.valid_type:
                continue
            for gi, g in enumerate(golds):
                if gi in used or not g.valid_type:
                    continue
                if getattr(r, key_of_run) == getattr(g, key_of_gold):
                    used.add(gi)
                    matched_run.add(ri)
                    res.exact.append((r, g))
                    break

    run_pass("strict_key", "strict_key")  # a relaxada também começa pelo que é idêntico
    if measure == "relaxada":
        run_pass("relaxed_key", "relaxed_key")

    res.golds_unmatched_exact = [g for i, g in enumerate(golds) if i not in used]
    snapshot = set(matched_run)  # só o acerto exato; o do pai vem depois

    for ri, r in enumerate(runs):
        if ri in matched_run or not r.valid_type:
            continue
        for gi, g in enumerate(golds):
            if gi in used or not g.valid_type:
                continue
            if _parent_hit(r, g, measure, ontology):
                used.add(gi)
                matched_run.add(ri)
                res.parent.append((r, g))
                break

    ignored = {
        i
        for i, r in enumerate(runs)
        if i not in matched_run and r.valid_type and r.relaxed_key in unproved_keys
    }
    res.ignored_unproved = len(ignored)
    res.considered = [r for i, r in enumerate(runs) if i not in ignored]
    res.runs_unmatched_exact = [
        r for i, r in enumerate(runs) if i not in snapshot and i not in ignored
    ]
    res.runs_unmatched = [
        r for i, r in enumerate(runs) if i not in matched_run and i not in ignored
    ]
    res.golds_unmatched = [g for i, g in enumerate(golds) if i not in used]
    return res


def parent_of(type_id: str, ontology: Ontology) -> str:
    """Pai imediato (`ancestors()[0]`); tipo sem pai ou inválido cai em NO_PARENT."""
    try:
        anc = ontology.ancestors(type_id)
    except OntologyLookupError:
        return NO_PARENT
    return anc[0] if anc else NO_PARENT


def _is_symmetric(type_id: str, ontology: Ontology) -> bool:
    return bool(getattr(ontology.get(type_id), "symmetric", False))


def _parent_hit(r: Item, g: Item, measure: Measure, ontology: Ontology) -> bool:
    """Mesmo par, tipo diferente, mesmo pai. A direção é exigida se os dois tipos
    são assimétricos e ignorada se um deles é simétrico."""
    if r.type_id == g.type_id or r.scope is not g.scope:
        return False
    pr = parent_of(r.type_id, ontology)
    if pr == NO_PARENT or pr != parent_of(g.type_id, ontology):
        return False
    if _is_symmetric(r.type_id, ontology) or _is_symmetric(g.type_id, ontology):
        same_pair = {r.subject, r.object_} == {g.subject, g.object_}
    else:
        same_pair = (r.subject, r.object_) == (g.subject, g.object_)
    if not same_pair:
        return False
    return measure == "relaxada" or r.asserted_by == g.asserted_by

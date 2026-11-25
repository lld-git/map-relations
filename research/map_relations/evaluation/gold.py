"""Formato do gabarito (B02 §3) e âncora de evidência (§4, ADR 012).

O gabarito vive em `data/golden/<obra>.json` (fora do Git) ou, para obras em
domínio público e fixtures sintéticas, em `eval/gold/`. Os nomes dos campos
seguem o formato aprovado no plano: `preferredName`, `startOffset` e
`endOffset` em camelCase; o resto em snake_case.

Duas camadas de validação:
- o modelo Pydantic cobre o que se decide olhando um objeto só (tipos,
  `asserted_by` se e somente se `alegada`, invariante interna da âncora);
- `validate_gold` cobre o que precisa de contexto: ontologia, referências
  entre objetos, duplicatas e o texto canônico.
"""

from __future__ import annotations

import enum
import json
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from map_relations.core.ids import claim_key
from map_relations.core.models import Claim, ClaimClass, NarrativeScope, RelationType
from map_relations.core.ontology import (
    AbstractTypeError,
    Ontology,
    OntologyLookupError,
    Status,
)

SCHEMA_VERSION = 1
HASH_PREFIX = "sha256:"
RELATION_ID_PREFIX = "r_"
RELATION_ID_LEN = 12  # hex da claim_key no id da relação


class _Model(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class Origin(enum.StrEnum):
    modelo = "modelo"
    humano = "humano"
    modelo_revisado = "modelo_revisado"


class Expected(enum.StrEnum):
    sem_relacao = "sem_relacao"


class Support(enum.StrEnum):
    """Quanto a evidência, sozinha, sustenta a relação (decisão do anotador)."""

    alto = "alto"
    medio = "medio"
    baixo = "baixo"


class Polarity(enum.StrEnum):
    apoia = "apoia"
    contradiz = "contradiz"


class Conjoint(enum.StrEnum):
    """`provas_em_conjunto`: o anotador declara que as evidências, juntas, bastam."""

    suficiente = "suficiente"


# Pesos e corte PROVISÓRIOS (ADR 012): a calibrar no B03 com execuções reais.
SUPPORT_WEIGHTS: dict[Support, int] = {Support.alto: 3, Support.medio: 2, Support.baixo: 1}
CONJOINT_CUTOFF = 4


# ── âncora (§4) ───────────────────────────────────────────────────────────────


class Anchor(_Model):
    """TextQuoteSelector (exact, prefix, suffix) + TextPositionSelector.

    Offsets em code points sobre o canônico NFC, fim exclusivo (ADR 004).
    A citação com o contexto é a verdade; a posição é o atalho.
    """

    exact: str = Field(min_length=1)
    prefix: str
    suffix: str
    start_offset: int = Field(alias="startOffset", ge=0)
    end_offset: int = Field(alias="endOffset", ge=1)

    @model_validator(mode="after")
    def _span_matches_exact(self) -> Anchor:
        if self.end_offset - self.start_offset != len(self.exact):
            raise ValueError(
                f"endOffset - startOffset ({self.end_offset - self.start_offset}) "
                f"≠ len(exact) ({len(self.exact)})"
            )
        return self


def check_anchor(anchor: Anchor, text: str) -> list[str]:
    """Confere a âncora contra o canônico; lista vazia = ok.

    Invariante: `text[start:end] == exact`, com `prefix` logo antes e `suffix`
    logo depois (cortados na borda do texto). Além disso, o contexto gravado
    precisa deixar a citação única no canônico (âncora mínima suficiente).
    """
    s, e = anchor.start_offset, anchor.end_offset
    if e > len(text):
        return [f"offset {e} além do fim do texto ({len(text)})"]
    errors: list[str] = []
    if text[s:e] != anchor.exact:
        errors.append("text[startOffset:endOffset] ≠ exact")
    if text[max(0, s - len(anchor.prefix)) : s] != anchor.prefix:
        errors.append("prefix não confere com o texto antes da citação")
    if text[e : e + len(anchor.suffix)] != anchor.suffix:
        errors.append("suffix não confere com o texto depois da citação")
    if not errors and _count(text, anchor.prefix + anchor.exact + anchor.suffix) != 1:
        errors.append("citação com contexto não é única no texto (aumente prefix/suffix)")
    return errors


def _count(text: str, needle: str) -> int:
    """Ocorrências de `needle` em `text`, contando as que se sobrepõem."""
    n, i = 0, text.find(needle)
    while i != -1:
        n += 1
        i = text.find(needle, i + 1)
    return n


# ── arquivo do gabarito (§3) ──────────────────────────────────────────────────


class GoldSource(_Model):
    content_hash: str = Field(pattern=rf"^{HASH_PREFIX}[0-9a-f]{{64}}$")
    offset_unit: Literal["codepoint_nfc"]
    end: Literal["exclusive"]


class GoldScope(_Model):
    chapters: list[str] = Field(min_length=1)
    narrative_scopes_evaluated: list[NarrativeScope] = Field(min_length=1)


class GoldEntity(_Model):
    # id legível, válido só dentro do arquivo (D1); não é o UUID do domínio
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    preferred_name: str = Field(alias="preferredName", min_length=1)
    aliases: list[str] = Field(default_factory=list)
    fictional: bool = False


class OriginDetail(_Model):
    model: str | None = None
    reviewed_by: str | None = None
    note: str | None = None


class GoldEvidence(_Model):
    """Uma evidência: só decisões de anotação. Nada calculado é gravado aqui
    (peso, perfil, situação da prova e capítulos extras vão só ao relatório)."""

    chapter: str = Field(min_length=1)  # conferido contra locate() na validação
    anchor: Anchor
    support: Support
    polarity: Polarity
    note: str | None = None


class GoldRelation(_Model):
    id: str
    subject: str
    type_: str = Field(alias="type")
    object_: str = Field(alias="object")
    class_: ClaimClass = Field(alias="class")
    asserted_by: str | None = None
    narrative_scope: NarrativeScope  # obrigatório: o anotador sempre decide
    origin: Origin
    origin_detail: OriginDetail | None = None
    evidence: list[GoldEvidence] = Field(min_length=1)  # princípio 4
    provas_em_conjunto: Conjoint | None = None
    fictional: bool = False

    @model_validator(mode="after")
    def _local_rules(self) -> GoldRelation:
        alegada = self.class_ is ClaimClass.alegada
        if alegada and not self.asserted_by:
            raise ValueError("class = alegada exige asserted_by")
        if not alegada and self.asserted_by is not None:
            raise ValueError("asserted_by só é permitido com class = alegada")
        if self.origin is not Origin.humano and not (
            self.origin_detail and self.origin_detail.model
        ):
            raise ValueError(f"origin = {self.origin.value} exige origin_detail.model")
        return self


class NegativePair(_Model):
    subject: str
    object_: str = Field(alias="object")
    chapters: list[str] = Field(min_length=1)
    expected: Expected
    fictional: bool = False


class GoldFile(_Model):
    schema_version: Literal[1]
    work: str = Field(min_length=1)
    source: GoldSource
    ontology_version: int = Field(ge=1)
    scope: GoldScope
    annotation_rules: list[str] = Field(default_factory=list)
    entities: list[GoldEntity]
    relations: list[GoldRelation]
    negative_pairs: list[NegativePair] = Field(default_factory=list)


def load_gold(path: Path) -> GoldFile:
    """Lê e valida a estrutura (Pydantic). Levanta ValidationError."""
    return GoldFile.model_validate(json.loads(path.read_text(encoding="utf-8")))


# ── validação com contexto (§3) ───────────────────────────────────────────────


class Canonical(Protocol):
    """O que a validação precisa do texto canônico; `IngestResult` satisfaz."""

    text: str

    @property
    def source(self) -> _HasHash: ...

    def paragraph_at(self, offset: int) -> _HasChapter: ...


class _HasHash(Protocol):
    content_hash: str


class _HasChapter(Protocol):
    chapter: int | None


@dataclass(frozen=True)
class ProofSummary:
    """Situação da prova de uma relação. Calculada, nunca gravada no gabarito."""

    proved: bool
    via: Literal["evidencia_alta", "conjunto", "nenhuma"]
    profile: dict[str, int]  # evidências que apoiam, por nível de suporte
    weight: int  # soma dos pesos das evidências que apoiam
    contradicting: int


def relation_proof(rel: GoldRelation) -> ProofSummary:
    """Provada se há evidência alta que apoia, ou se `provas_em_conjunto = suficiente`.
    O peso não decide: só alimenta o alerta de `validate_gold`."""
    supporting = [e for e in rel.evidence if e.polarity is Polarity.apoia]
    profile = {level.value: 0 for level in Support}
    for e in supporting:
        profile[e.support.value] += 1
    weight = sum(SUPPORT_WEIGHTS[e.support] for e in supporting)
    contradicting = len(rel.evidence) - len(supporting)
    if profile[Support.alto.value]:
        via: Literal["evidencia_alta", "conjunto", "nenhuma"] = "evidencia_alta"
    elif rel.provas_em_conjunto is Conjoint.suficiente:
        via = "conjunto"
    else:
        via = "nenhuma"
    return ProofSummary(via != "nenhuma", via, profile, weight, contradicting)


@dataclass
class GoldReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    proofs: dict[str, ProofSummary] = field(default_factory=dict)  # por id de relação

    @property
    def ok(self) -> bool:
        return not self.errors


def relation_id(rel: GoldRelation, ontology: Ontology) -> str:
    """Id estável da relação: `r_` + início da `claim_key` (simetria lida do tipo)."""
    type_id, s, o = ontology.canonicalize(rel.type_, rel.subject, rel.object_)
    rt = _relation_types(ontology)[type_id]
    key = claim_key(
        s,
        rt,
        o,
        asserted_by=rel.asserted_by,
        narrative_scope=rel.narrative_scope.value,
    )
    return RELATION_ID_PREFIX + key[:RELATION_ID_LEN]


def _relation_types(ontology: Ontology) -> dict[str, RelationType]:
    return {rt.id: rt for rt in ontology.relation_types()}


def validate_gold(
    gold: GoldFile, ontology: Ontology, canonical: Canonical | None = None
) -> GoldReport:
    """Regras do §3 que dependem de contexto. Itens `fictional` não citam a obra:
    suas âncoras não são conferidas contra o canônico."""
    rep = GoldReport()
    err = rep.errors.append

    if gold.ontology_version != ontology.version:
        err(
            f"ontology_version {gold.ontology_version} ≠ versão da ontologia "
            f"({ontology.version})"
        )

    entity_ids = [e.id for e in gold.entities]
    for dup in _duplicates(entity_ids):
        err(f"entidade: id repetido '{dup}'")
    known = set(entity_ids)

    keys: dict[str, str] = {}
    for rel in gold.relations:
        _check_relation(rel, ontology, known, keys, err)

    for pair in gold.negative_pairs:
        for ref in (pair.subject, pair.object_):
            if ref not in known:
                err(f"par de controle {pair.subject}/{pair.object_}: entidade '{ref}' não existe")

    _report_proofs(gold, rep)
    _warn_disjoint(gold, ontology, rep)

    if canonical is None:
        rep.warnings.append("sem canônico: âncoras e pares de controle não foram conferidos")
        return rep
    _check_canonical(gold, canonical, rep)
    return rep


def _duplicates(items: Iterable[str]) -> list[str]:
    return [k for k, n in Counter(items).items() if n > 1]


def _check_relation(
    rel: GoldRelation,
    ontology: Ontology,
    known: set[str],
    keys: dict[str, str],
    err: Callable[[str], None],
) -> None:
    tag = f"relação {rel.id}"
    for ref in (rel.subject, rel.object_, rel.asserted_by):
        if ref is not None and ref not in known:
            err(f"{tag}: entidade '{ref}' não existe")
    try:
        type_id, s, o = ontology.canonicalize(rel.type_, rel.subject, rel.object_)
    except AbstractTypeError:
        err(f"{tag}: tipo '{rel.type_}' é abstrato, não anotável")
        return
    except OntologyLookupError:
        err(f"{tag}: tipo '{rel.type_}' não existe na ontologia")
        return
    definition = ontology.get(type_id)
    if getattr(definition, "status", None) is Status.obsolete:
        err(f"{tag}: tipo '{type_id}' é obsoleto")
    if getattr(definition, "irreflexive", False) and s == o:
        err(f"{tag}: tipo '{type_id}' não admite sujeito igual ao objeto")

    expected = relation_id(rel, ontology)
    if rel.id != expected:
        err(f"{tag}: id deveria ser '{expected}' (derivado da claim_key)")
    # `expected` já embute simetria, asserted_by e escopo; repetida = mesma claim_key
    if expected in keys:
        err(f"{tag}: duplica a relação {keys[expected]} (mesma claim_key)")
    else:
        keys[expected] = rel.id


def _report_proofs(gold: GoldFile, rep: GoldReport) -> None:
    for rel in gold.relations:
        proof = relation_proof(rel)
        rep.proofs[rel.id] = proof
        if rel.provas_em_conjunto is Conjoint.suficiente and proof.weight < CONJOINT_CUTOFF:
            rep.warnings.append(
                f"relação {rel.id}: provas_em_conjunto = suficiente, mas a soma dos pesos "
                f"({proof.weight}) fica abaixo do corte ({CONJOINT_CUTOFF}; "
                "provisório, calibrar no B03)"
            )
        if not proof.proved:
            rep.warnings.append(
                f"relação {rel.id}: sem prova (nenhuma evidência alta que apoia e "
                "provas_em_conjunto não declarado)"
            )


def _warn_disjoint(gold: GoldFile, ontology: Ontology, rep: GoldReport) -> None:
    claims: list[Claim] = []
    for rel in gold.relations:
        try:
            type_id, s, o = ontology.canonicalize(rel.type_, rel.subject, rel.object_)
        except (AbstractTypeError, OntologyLookupError):
            continue  # já reportado como erro
        claims.append(
            Claim.model_construct(
                id=rel.id,
                claim_key=rel.id,
                subject_id=s,
                type_id=type_id,
                object_id=o,
                claim_class=rel.class_,
                confidence=1.0,
                pass_id="gold",
            )
        )
    for c in ontology.disjoint_conflicts(claims):
        rep.warnings.append(
            f"disjunção: relações {c.claim_a.id} e {c.claim_b.id} (mesmo par, tipos disjuntos)"
        )


def _check_canonical(gold: GoldFile, canonical: Canonical, rep: GoldReport) -> None:
    err = rep.errors.append
    actual = HASH_PREFIX + canonical.source.content_hash
    if gold.source.content_hash != actual:
        err(
            f"content_hash do gabarito ({gold.source.content_hash[:15]}…) ≠ canônico atual "
            f"({actual[:15]}…): rode fill-offsets"
        )
        return  # com hash diferente, toda âncora seria ruído
    chapters_of: dict[frozenset[str], set[str]] = {}
    for rel in gold.relations:
        if rel.fictional:
            continue
        chapters: set[str] = set()
        for i, ev in enumerate(rel.evidence):
            anchor_errors = check_anchor(ev.anchor, canonical.text)
            for msg in anchor_errors:
                err(f"relação {rel.id}, evidência {i}: {msg}")
            if ev.anchor.end_offset <= len(canonical.text):
                ch = canonical.paragraph_at(ev.anchor.start_offset).chapter
                actual = "" if ch is None else str(ch)
                chapters.add(actual)
                if ev.chapter != actual:
                    err(
                        f"relação {rel.id}, evidência {i}: chapter '{ev.chapter}' ≠ capítulo "
                        f"do trecho ('{actual}')"
                    )
        chapters_of.setdefault(frozenset((rel.subject, rel.object_)), set()).update(chapters)
    for pair in gold.negative_pairs:
        if pair.fictional:
            continue
        hit = chapters_of.get(frozenset((pair.subject, pair.object_)), set()) & set(pair.chapters)
        if hit:
            err(
                f"par de controle {pair.subject}/{pair.object_}: há relação no mesmo par "
                f"nos capítulos {sorted(hit)}"
            )

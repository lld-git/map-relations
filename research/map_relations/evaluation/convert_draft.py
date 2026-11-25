"""`gold convert-draft` (B02 §6): rascunho legado → `GoldFile`, uso único.

O rascunho tem entidades sem id, relações com nomes e offsets velhos. A
conversão resolve nomes em ids, renomeia tipos pela tabela fixa, descarta os
offsets antigos e refaz cada âncora pela mesma rotina do fill-offsets.

Tudo ou nada. O relatório só tem ids, contagens e referências "cap. X, § Y";
a citação ambígua mostra no máximo cinco palavras de cada lado, nunca a citação.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from pydantic import ValidationError

from map_relations.core.ingest_contract import IngestResult
from map_relations.core.models import ClaimClass
from map_relations.core.ontology import (
    AbstractTypeError,
    Ontology,
    OntologyLookupError,
    Status,
)
from map_relations.evaluation.anchoring import (
    AnchorErrorKind,
    AnchorInput,
    AnchorResolved,
    resolve_anchor,
    words_around,
)
from map_relations.evaluation.gold import (
    HASH_PREFIX,
    GoldFile,
    GoldRelation,
    Polarity,
    Support,
    relation_id,
    validate_gold,
)

# O id antigo nunca foi publicado na trava da ontologia (A5).
TYPE_RENAMES = {"vigia": "exerce_vigilancia_sobre"}
NO_RELATION_TEXT = "nenhuma relação de nenhum tipo"
UNKNOWN_MODEL = "desconhecido"


def slugify(name: str) -> str:
    """casefold, sem acentos, `_` entre grupos alfanuméricos; começa por letra."""
    folded = unicodedata.normalize("NFKD", name.casefold())
    ascii_ = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", ascii_).strip("_")


def parse_chapters(scope: str) -> list[str] | None:
    """'capítulos 1-3' → ['1','2','3']; 'capítulo 2' → ['2']; None se não entender."""
    m = re.fullmatch(r"\s*cap[ií]tulos?\s+(.+?)\s*", scope, flags=re.IGNORECASE)
    if not m:
        return None
    chapters: list[str] = []
    for part in re.split(r"\s*(?:,|;|\be\b)\s*", m.group(1)):
        r = re.fullmatch(r"(\d+)\s*[-–]\s*(\d+)", part)
        if r and int(r.group(1)) <= int(r.group(2)):
            chapters += [str(n) for n in range(int(r.group(1)), int(r.group(2)) + 1)]
        elif re.fullmatch(r"\d+", part):
            chapters.append(part)
        else:
            return None
    return chapters or None


@dataclass
class RelationOutcome:
    index: int
    summary: str  # "sujeito tipo objeto" (nomes de entidades, sem texto da obra)
    errors: list[str] = field(default_factory=list)
    where: str | None = None
    # citação ambígua: candidatas com referência e palavras em volta
    ambiguous: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class ConversionReport:
    relations: list[RelationOutcome] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # entidades, controle, validação final
    warnings: list[str] = field(default_factory=list)
    narrative_scope_defaulted: int = 0  # relações a que se atribuiu `obra` (A3)

    @property
    def converted(self) -> int:
        return sum(1 for r in self.relations if r.ok)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.relations if not r.ok)

    @property
    def ok(self) -> bool:
        return not self.errors and self.failed == 0

    @property
    def decisions(self) -> list[RelationOutcome]:
        return [r for r in self.relations if r.ambiguous]

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "converted": self.converted,
            "failed": self.failed,
            "narrative_scope_defaulted": self.narrative_scope_defaulted,
            "errors": self.errors,
            "warnings": self.warnings,
            "relations": [asdict(r) for r in self.relations if not r.ok],
        }

    def render(self) -> str:
        lines = [
            f"relações convertidas: {self.converted}",
            f"relações com erro:    {self.failed}",
            f"narrative_scope = obra atribuído a {self.narrative_scope_defaulted} (confirmar)",
        ]
        for r in self.relations:
            if r.ambiguous:
                lines.append(f"\nDECISÃO — relação #{r.index} ({r.summary}): citação ambígua")
                for c in r.ambiguous:
                    mark = " (a que o rascunho usava)" if c["draft_used"] else ""
                    ctx = f"…{c['before']} […] {c['after']}…"
                    lines.append(f"  [{c['n']}] {c['where']}{mark}: {ctx}")
                lines.append(
                    "  Escolha olhando só isso e acrescente \"prefix\" à relação no rascunho: o "
                    "texto idêntico que vem logo antes da citação (as palavras acima, com os "
                    "espaços e quebras de linha do texto)."
                )
            else:
                for e in r.errors:
                    lines.append(f"\nERRO — relação #{r.index} ({r.summary}): {e}")
        lines += [f"\nERRO: {e}" for e in self.errors]
        lines += [f"aviso: {w}" for w in self.warnings]
        return "\n".join(lines)


def convert_draft(
    draft: dict[str, Any], canon: IngestResult, ontology: Ontology
) -> tuple[dict[str, Any] | None, ConversionReport]:
    """Devolve (gabarito como dict pronto para gravar, relatório); None se houver erro."""
    rep = ConversionReport()
    entities, names = _convert_entities(draft, rep)
    pairs = _convert_pairs(draft, names, rep)
    relations: list[dict[str, Any]] = []
    for i, raw in enumerate(draft.get("relations", [])):
        outcome, rel = _convert_relation(i, raw, names, canon, ontology)
        rep.relations.append(outcome)
        if rel is not None:
            relations.append(rel)
            rep.narrative_scope_defaulted += 1
    if not rep.ok:
        return None, rep

    scope = draft.get("scope", {})
    data = {
        "schema_version": 1,
        "work": draft.get("work", ""),
        "source": {
            "content_hash": HASH_PREFIX + canon.source.content_hash,
            "offset_unit": "codepoint_nfc",
            "end": "exclusive",
        },
        "ontology_version": ontology.version,
        "scope": {
            "chapters": [str(c) for c in scope.get("chapters", [])],
            "narrative_scopes_evaluated": ["obra"],
        },
        "annotation_rules": list(draft.get("rules", [])),
        "entities": entities,
        "relations": relations,
        "negative_pairs": pairs,
    }
    try:
        gold = GoldFile.model_validate(data)
    except ValidationError as exc:
        rep.errors.append(f"gabarito convertido inválido ({exc.error_count()} erro(s) de formato)")
        rep.errors += [
            "  " + ".".join(str(p) for p in e["loc"]) + f": {e['msg']}" for e in exc.errors()[:5]
        ]
        return None, rep
    final = validate_gold(gold, ontology, canon)
    rep.errors += final.errors
    rep.warnings += final.warnings
    if not rep.ok:
        return None, rep
    return gold.model_dump(by_alias=True, mode="json", exclude_none=True), rep


def _convert_entities(
    draft: dict[str, Any], rep: ConversionReport
) -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    entities: list[dict[str, Any]] = []
    names: dict[str, set[str]] = {}
    seen: dict[str, str] = {}
    for raw in draft.get("entities", []):
        name = raw["preferredName"]
        eid = slugify(name)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", eid):
            rep.errors.append(f"entidade '{name}': slug '{eid}' inválido")
            continue
        if eid in seen:
            rep.errors.append(f"entidades '{seen[eid]}' e '{name}' dão o mesmo id '{eid}'")
            continue
        seen[eid] = name
        aliases = list(raw.get("aliases", []))
        entities.append({"id": eid, "preferredName": name, "aliases": aliases})
        for label in (name, *aliases):
            names.setdefault(label, set()).add(eid)
    return entities, names


def _resolve_name(
    label: str, what: str, names: dict[str, set[str]], errors: list[str]
) -> str | None:
    ids = names.get(label, set())
    if len(ids) == 1:
        return next(iter(ids))
    errors.append(
        f"{what} '{label}': " + ("nenhuma entidade casa" if not ids else f"casa com {len(ids)}")
    )
    return None


def _convert_pairs(
    draft: dict[str, Any], names: dict[str, set[str]], rep: ConversionReport
) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for i, raw in enumerate(draft.get("negative_pairs", [])):
        errs: list[str] = []
        s = _resolve_name(raw["subject"], "sujeito", names, errs)
        o = _resolve_name(raw["object"], "objeto", names, errs)
        chapters = parse_chapters(raw.get("scope", ""))
        if chapters is None:
            errs.append(f"escopo '{raw.get('scope')}' não reconhecido")
        if raw.get("expected") != NO_RELATION_TEXT:
            errs.append(f"resultado esperado '{raw.get('expected')}' não reconhecido")
        if errs:
            rep.errors += [f"par de controle #{i}: {e}" for e in errs]
            continue
        pairs.append(
            {"subject": s, "object": o, "chapters": chapters, "expected": "sem_relacao"}
        )
    return pairs


def _convert_relation(
    index: int,
    raw: dict[str, Any],
    names: dict[str, set[str]],
    canon: IngestResult,
    ontology: Ontology,
) -> tuple[RelationOutcome, dict[str, Any] | None]:
    outcome = RelationOutcome(index, f"{raw.get('subject')} {raw.get('type')} {raw.get('object')}")
    errs = outcome.errors
    s = _resolve_name(raw["subject"], "sujeito", names, errs)
    o = _resolve_name(raw["object"], "objeto", names, errs)
    by = raw.get("asserted_by")
    by_id = _resolve_name(by, "asserted_by", names, errs) if by is not None else None

    type_in = TYPE_RENAMES.get(raw["type"], raw["type"])
    type_id: str | None = None
    if s is not None and o is not None:
        try:
            type_id, s, o = ontology.canonicalize(type_in, s, o)
        except AbstractTypeError:
            errs.append(f"tipo '{type_in}' é abstrato, não anotável")
        except OntologyLookupError:
            errs.append(f"tipo '{type_in}' não existe na ontologia")
        else:
            if getattr(ontology.get(type_id), "status", None) is Status.obsolete:
                errs.append(f"tipo '{type_id}' é obsoleto")
    try:
        cls = ClaimClass(raw["class"])
    except ValueError:
        errs.append(f"classe '{raw['class']}' fora do contrato")
        cls = None

    anchor = _resolve_quote(raw, canon, outcome)
    if errs or anchor is None or cls is None:
        return outcome, None

    draft_chapter = str(raw.get("chapter", ""))
    actual = canon.paragraph_at(anchor["startOffset"]).chapter
    outcome.where = canon.locate(anchor["startOffset"])
    if draft_chapter != ("" if actual is None else str(actual)):
        errs.append(f"capítulo do rascunho ({draft_chapter}) ≠ {outcome.where}")
        return outcome, None

    candidate = {
        "id": "",
        "subject": s,
        "type": type_id,
        "object": o,
        "class": cls.value,
        "asserted_by": by_id,
        "narrative_scope": "obra",  # A3: o rascunho não tem; fica para o humano confirmar
        "origin": "modelo",
        "origin_detail": {"model": raw.get("model") or UNKNOWN_MODEL},
        # o rascunho tem uma citação por relação: uma evidência alta que apoia
        "evidence": [
            {
                "chapter": draft_chapter,
                "anchor": anchor,
                "support": Support.alto.value,
                "polarity": Polarity.apoia.value,
            }
        ],
    }
    try:
        rel = GoldRelation.model_validate(candidate)
    except ValidationError as exc:
        errs += [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return outcome, None
    rel = rel.model_copy(update={"id": relation_id(rel, ontology)})
    return outcome, rel.model_dump(by_alias=True, mode="json", exclude_none=True)


def _resolve_quote(
    raw: dict[str, Any], canon: IngestResult, outcome: RelationOutcome
) -> dict[str, Any] | None:
    """Âncora da citação do rascunho. Os offsets antigos (A1) são descartados;
    `prefix`/`suffix` opcionais no rascunho são o jeito de o humano decidir (D4)."""
    entry = AnchorInput(
        exact=raw["quote"], prefix=raw.get("prefix", ""), suffix=raw.get("suffix", "")
    )
    res = resolve_anchor(canon.text, entry)
    if isinstance(res, AnchorResolved):
        return res.anchor.model_dump(by_alias=True)
    if res.kind is AnchorErrorKind.nao_encontrada:
        outcome.errors.append("nao_encontrada: a citação não existe no canônico atual")
        return None
    outcome.errors.append(f"ambigua: {len(res.candidates)} ocorrências no canônico")
    used = raw.get("occurrence_used")
    for n, occ in enumerate(res.candidates, start=1):
        par = canon.paragraph_at(occ.start)
        before, after = words_around(
            canon.text, occ.start, occ.end, (par.start_offset, par.end_offset)
        )
        outcome.ambiguous.append(
            {
                "n": n,
                "where": canon.locate(occ.start),
                "draft_used": used == n,
                "before": before,
                "after": after,
            }
        )
    return None


__all__ = ["ConversionReport", "convert_draft", "parse_chapters", "slugify"]

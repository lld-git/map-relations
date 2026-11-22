"""`gold fill-offsets` (B02 §5): refaz as âncoras de um gabarito sobre o canônico atual.

Tudo ou nada: com qualquer erro nada é gravado. O relatório não carrega texto
da obra: só ids, posições, referências "cap. X, § Y" e contagens.
"""

from __future__ import annotations

import copy
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from map_relations.core.ingest_contract import IngestResult
from map_relations.evaluation.anchoring import (
    AnchorError,
    AnchorInput,
    AnchorResolved,
    resolve_anchor,
)
from map_relations.evaluation.gold import HASH_PREFIX, GoldFile
from map_relations.ingest.document import compute_text_hash


class CanonicalError(Exception):
    """Canônico ausente, ilegível ou inconsistente com o seu ingest.json."""


def load_canonical(path: Path) -> IngestResult:
    """Carrega `canonical.txt` + `ingest.json` (mesma pasta de data/processed/<hash>/)."""
    ingest = path.parent / "ingest.json"
    if not path.is_file() or not ingest.is_file():
        raise CanonicalError(f"esperado canonical.txt e ingest.json em {path.parent}")
    text = path.read_bytes().decode("utf-8")  # sem conversão de quebra de linha
    data = json.loads(ingest.read_text(encoding="utf-8"))
    data["text"] = text
    result = IngestResult.model_validate(data)
    if compute_text_hash(text) != result.source.content_hash:
        raise CanonicalError(f"canonical.txt não confere com o hash de {ingest}")
    return result


def default_canonical(processed: Path) -> Path:
    """Único canonical.txt em `processed`; qualquer outro caso é erro (sem chute)."""
    found = sorted(processed.glob("*/canonical.txt"))
    if len(found) != 1:
        raise CanonicalError(
            f"{len(found)} documentos em {processed}; informe --canonical explicitamente"
        )
    return found[0]


@dataclass
class EvidenceOutcome:
    relation: str
    evidence: int
    status: str  # inalterada | preenchida | posicao_nova | contexto_atualizado | erro
    old_start: int | None = None
    new_start: int | None = None
    where: str | None = None  # "cap. X, § Y"
    detail: str | None = None  # mensagem de erro/aviso, sem texto da obra
    # erro `ambigua`: candidatas com a referência de capítulo e parágrafo
    candidates: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FillReport:
    outcomes: list[EvidenceOutcome] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)  # erros que não são de uma evidência

    @property
    def ok(self) -> bool:
        return not self.errors and all(o.status != "erro" for o in self.outcomes)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for o in self.outcomes:
            out[o.status] = out.get(o.status, 0) + 1
        return out

    def to_json(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "counts": self.counts(),
            "errors": self.errors,
            "outcomes": [asdict(o) for o in self.outcomes],
        }

    def render_table(self) -> str:
        lines = [f"{'relação':<22} {'ev':>2}  {'situação':<20} posição"]
        for o in self.outcomes:
            if o.status == "inalterada":
                continue
            pos = f"{o.old_start}→{o.new_start}" if o.new_start is not None else "-"
            note = f"  {o.where}" if o.where else ""
            lines.append(f"{o.relation:<22} {o.evidence:>2}  {o.status:<20} {pos}{note}")
            if o.detail:
                lines.append(f"    {o.detail}")
            for c in o.candidates:
                lines.append(f"    candidata {c['start']}: {c['where']}")
        lines += [f"erro: {e}" for e in self.errors]
        resumo = ", ".join(f"{n} {k}" for k, n in sorted(self.counts().items())) or "nada a fazer"
        lines.append(f"total: {resumo}")
        return "\n".join(lines)


def _where(canon: IngestResult, offset: int) -> str:
    return canon.locate(offset)


def resolve_evidence(
    canon: IngestResult, relation: str, index: int, raw: dict[str, Any]
) -> tuple[EvidenceOutcome, dict[str, Any] | None]:
    """Uma evidência: o resultado do relatório e a âncora nova (None se erro)."""
    try:
        entry = AnchorInput.model_validate(raw)
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first["loc"])
        return EvidenceOutcome(relation, index, "erro", detail=f"{loc}: {first['msg']}"), None
    res = resolve_anchor(canon.text, entry)
    if isinstance(res, AnchorError):
        out = EvidenceOutcome(relation, index, "erro", old_start=entry.start_offset)
        if res.kind.value == "nao_encontrada":
            out.detail = "nao_encontrada: a citação não existe no canônico atual"
        else:
            out.detail = (
                f"ambigua: {len(res.candidates)} ocorrências, "
                f"{res.matching_context} batem com o contexto gravado"
            )
            out.candidates = [
                {"start": c.start, "end": c.end, "where": _where(canon, c.start)}
                for c in res.candidates
            ]
        return out, None
    assert isinstance(res, AnchorResolved)
    if res.filled:
        status = "preenchida"
    elif res.moved:
        status = "posicao_nova"
    elif res.context_updated:
        status = "contexto_atualizado"
    else:
        status = "inalterada"
    out = EvidenceOutcome(
        relation,
        index,
        status,
        old_start=res.old_start,
        new_start=res.anchor.start_offset,
        where=_where(canon, res.anchor.start_offset),
    )
    if res.moved and res.context_updated:
        out.detail = "contexto atualizado"
    return out, res.anchor.model_dump(by_alias=True)


def fill_offsets(
    gold: dict[str, Any], canon: IngestResult
) -> tuple[dict[str, Any] | None, FillReport]:
    """Devolve (gabarito novo, relatório). Com qualquer erro o gabarito é None.

    Entrada e saída são dicts: a entrada pode ter evidências só com `exact`, que
    ainda não são um `GoldFile` válido. Itens `fictional` não citam a obra e
    ficam como estão. A entrada nunca é alterada.
    """
    report = FillReport()
    out = copy.deepcopy(gold)
    relations = out.get("relations")
    if not isinstance(relations, list):
        report.errors.append("gabarito sem lista 'relations'")
        return None, report
    for i, rel in enumerate(relations):
        if not isinstance(rel, dict) or rel.get("fictional"):
            continue
        label = str(rel.get("id") or f"#{i}")
        evidence = rel.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            report.errors.append(f"relação {label}: sem evidência (princípio 4)")
            continue
        for j, raw in enumerate(evidence):
            entry = raw if isinstance(raw, dict) else {}
            outcome, anchor = resolve_evidence(canon, label, j, entry)
            report.outcomes.append(outcome)
            if anchor is not None:
                evidence[j] = anchor
    if not report.ok:
        return None, report
    source = out.setdefault("source", {})
    source["content_hash"] = HASH_PREFIX + canon.source.content_hash
    try:
        GoldFile.model_validate(out)
    except ValidationError as exc:
        report.errors.append(f"gabarito de saída inválido: {exc.error_count()} erro(s) de formato")
        for e in exc.errors()[:5]:
            report.errors.append("  " + ".".join(str(p) for p in e["loc"]) + f": {e['msg']}")
        return None, report
    return out, report

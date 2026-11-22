"""Subcomandos `gold ...` da CLI (B02 §5 e §6). Sem caminho padrão para data/golden/.

Códigos de saída: 0 ok; 1 erros de âncora/conversão/validação (nada gravado);
2 entrada inválida (arquivo ausente, JSON ruim, `--out` igual à entrada).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from map_relations.core.ingest_contract import IngestResult
from map_relations.evaluation.convert_draft import convert_draft
from map_relations.evaluation.fill_offsets import (
    CanonicalError,
    default_canonical,
    fill_offsets,
    load_canonical,
)
from map_relations.evaluation.gold import load_gold, validate_gold
from map_relations.ontology_io import load_ontology


def _err(msg: str) -> int:
    print(f"erro: {msg}", file=sys.stderr)
    return 2


def _canonical(arg: Path | None, processed: Path) -> IngestResult:
    return load_canonical(arg if arg is not None else default_canonical(processed))


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("o JSON deve ser um objeto")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _same_file(a: Path, b: Path) -> bool:
    return a.resolve() == b.resolve()


def cmd_fill_offsets(
    gold: Path, canonical: Path | None, out: Path, report: Path | None, processed: Path
) -> int:
    if _same_file(out, gold):
        return _err("--out não pode ser igual a --gold (a entrada nunca é sobrescrita)")
    try:
        canon = _canonical(canonical, processed)
        data = _read_json(gold)
    except (CanonicalError, OSError, ValueError) as exc:
        return _err(str(exc))
    new, rep = fill_offsets(data, canon)
    print(rep.render_table())
    if report is not None:
        _write_json(report, rep.to_json())
    if new is None:
        print("nada foi gravado (tudo ou nada)", file=sys.stderr)
        return 1
    _write_json(out, new)
    print(f"gravado: {out}")
    return 0


def cmd_convert_draft(
    draft: Path, canonical: Path | None, out: Path, report: Path | None, processed: Path
) -> int:
    if _same_file(out, draft):
        return _err("--out não pode ser igual a --draft (o rascunho fica intocado)")
    try:
        canon = _canonical(canonical, processed)
        data = _read_json(draft)
    except (CanonicalError, OSError, ValueError) as exc:
        return _err(str(exc))
    try:
        new, rep = convert_draft(data, canon, load_ontology())
    except (KeyError, TypeError) as exc:
        return _err(f"rascunho fora do formato esperado: {type(exc).__name__} {exc}")
    print(rep.render())
    if report is not None:
        _write_json(report, rep.to_json())
    if new is None:
        print("\nnada foi gravado (tudo ou nada)", file=sys.stderr)
        return 1
    _write_json(out, new)
    print(f"\ngravado: {out}")
    return 0


def cmd_validate(gold: Path, canonical: Path | None, processed: Path) -> int:
    try:
        canon = _canonical(canonical, processed)
        parsed = load_gold(gold)
    except (CanonicalError, OSError, ValueError, ValidationError) as exc:
        return _err(str(exc).splitlines()[0])
    rep = validate_gold(parsed, load_ontology(), canon)
    for e in rep.errors:
        print(f"erro: {e}")
    for w in rep.warnings:
        print(f"aviso: {w}")
    print(
        f"gabarito: {len(parsed.relations)} relações, {len(parsed.entities)} entidades, "
        f"{len(parsed.negative_pairs)} pares de controle — "
        f"{len(rep.errors)} erro(s), {len(rep.warnings)} aviso(s)"
    )
    return 0 if rep.ok else 1

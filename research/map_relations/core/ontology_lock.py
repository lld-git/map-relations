"""Trava de ids da ontologia (ADR 011): impede apagar, reaproveitar ou mudar ids.

Puro, sem I/O. Para cada id já publicado (tipo, abstrato, visão inversa) a trava
guarda o tipo de entrada, o último `version`, o hash dos campos semânticos e o
hash do conteúdo editorial. A trava só acrescenta entradas.

Tipos abstratos não têm `version`: só a parte semântica é protegida neles.
Visão inversa herda o `version` do tipo dono.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from map_relations.core.ontology import Ontology, OntologyError, Status

SEMANTIC_FIELDS = ("definition", "domain", "range", "symmetric", "irreflexive", "parent")
_NOT_EDITORIAL = {"version", "status", "replaced_by"}


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _entries(onto: Ontology) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for a in onto.file.abstract_types:
        d = a.model_dump(mode="json")
        out[a.id] = {
            "kind": "abstract",
            "version": None,
            "status": a.status.value,
            "semantic": _hash({k: d[k] for k in ("definition", "domain", "range")}),
            "content": _hash({k: v for k, v in d.items() if k not in _NOT_EDITORIAL}),
        }
    for t in onto.file.types:
        d = t.model_dump(mode="json")
        out[t.id] = {
            "kind": "type",
            "version": t.version,
            "status": t.status.value,
            "semantic": _hash({k: d[k] for k in SEMANTIC_FIELDS}),
            "content": _hash({k: v for k, v in d.items() if k not in _NOT_EDITORIAL}),
        }
        if t.inverse_of is not None:
            out[t.inverse_of.id] = {
                "kind": "inverse",
                "version": t.version,
                "status": "active",
                "semantic": _hash({"owner": t.id}),
                "content": _hash(t.inverse_of.model_dump(mode="json")),
            }
    return out


def update_lock(onto: Ontology, previous: Mapping[str, Any] | None) -> dict[str, Any]:
    """Devolve a trava nova; levanta OntologyError se alguma regra for violada."""
    old: Mapping[str, Any] = (previous or {}).get("ids", {})
    new = _entries(onto)
    errs: list[str] = []
    for id_, prev in old.items():
        cur = new.get(id_)
        if cur is None:
            errs.append(f"lock[{id_}]: id publicado sumiu do YAML (use status: obsolete)")
            continue
        if cur["kind"] != prev["kind"]:
            errs.append(f"lock[{id_}]: tipo de entrada mudou de {prev['kind']} para {cur['kind']}")
            continue
        if cur["semantic"] != prev["semantic"]:
            errs.append(f"lock[{id_}]: campo semântico mudou com o mesmo id (crie um id novo)")
        pv, cv = prev["version"], cur["version"]
        if pv is not None:
            if cv < pv:
                errs.append(f"lock[{id_}]: version caiu de {pv} para {cv}")
            elif cur["content"] != prev["content"] and cv == pv:
                errs.append(f"lock[{id_}]: conteúdo mudou sem subir version ({pv})")
        if prev["status"] == Status.obsolete.value and cur["status"] == Status.active.value:
            errs.append(f"lock[{id_}]: id obsoleto voltou a active")
    if errs:
        raise OntologyError(errs)
    merged = {**old, **new}
    return {"ids": dict(sorted(merged.items()))}

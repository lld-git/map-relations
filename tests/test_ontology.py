"""Ontologia de relações (B02a): validação, consultas, trava e geração."""

import copy
import json
from pathlib import Path

import pytest

from map_relations.core.models import Claim, ClaimClass, RelationType
from map_relations.core.ontology import (
    AbstractTypeError,
    OntologyError,
    OntologyLookupError,
    build_ontology,
    check_parent_chain,
)
from map_relations.core.ontology_lock import update_lock
from map_relations.ontology_io import load_ontology
from scripts import generate_ontology
from scripts.generate_ontology import render_all

REAL = Path(generate_ontology.YAML_PATH)


def _abstract(id_="fam"):
    return {
        "id": id_,
        "label": "Família",
        "definition": "d",
        "domain": ["pessoa"],
        "range": ["pessoa"],
    }


def _type(id_, parent="fam", symmetric=False, **extra):
    t = {
        "id": id_,
        "version": 1,
        "label": id_,
        "definition": f"def {id_}",
        "when_to_use": "x",
        "when_not_to_use": "y",
        "example": "z",
        "parent": parent,
        "domain": ["pessoa"],
        "range": ["pessoa"],
        "symmetric": symmetric,
        "irreflexive": True,
    }
    if not symmetric:
        t["inverse_of"] = {"id": f"{id_}_inv", "label": f"{id_} inv"}
    t.update(extra)
    return t


def _data(*types, abstracts=None):
    return {
        "version": 1,
        "abstract_types": abstracts if abstracts is not None else [_abstract()],
        "types": list(types) or [_type("a"), _type("b", symmetric=True)],
    }


def _errors(data):
    with pytest.raises(OntologyError) as exc:
        build_ontology(data)
    return exc.value.errors


def _has(errors, *parts):
    assert any(all(p in e for p in parts) for e in errors), errors


def _claim(s, t, o):
    return Claim(
        claim_key="k", subject_id=s, type_id=t, object_id=o,
        claim_class=ClaimClass.afirmada, confidence=0.5, pass_id="p",
    )  # fmt: skip


# ── arquivo real ─────────────────────────────────────────────────────────────


def test_real_file_loads_with_expected_counts():
    onto = load_ontology(REAL)
    assert onto.n_annotatable == 12
    assert onto.n_abstract == 5
    assert onto.version == 1


def test_minimal_valid():
    assert build_ontology(_data()).n_annotatable == 2


# ── erros ────────────────────────────────────────────────────────────────────


def test_duplicate_id_between_type_and_inverse():
    d = _data(_type("a"), _type("b", symmetric=True))
    d["types"][0]["inverse_of"]["id"] = "b"
    _has(_errors(d), "duplicado", "'b'")


def test_duplicate_id_between_abstract_and_type():
    _has(_errors(_data(_type("fam"))), "duplicado", "'fam'")


def test_unknown_key():
    d = _data()
    d["types"][0]["definicao"] = "x"
    _has(_errors(d), "types[a].definicao", "Extra inputs")


def test_id_out_of_format():
    d = _data(_type("Bad-Id", symmetric=True))
    _has(_errors(d), "fora do formato", "'Bad-Id'")


def test_abstract_with_parent():
    d = _data(abstracts=[{**_abstract(), "parent": "x"}])
    _has(_errors(d), "abstract_types[fam].parent", "abstrato não tem parent")


def test_annotatable_without_parent():
    t = _type("a")
    del t["parent"]
    _has(_errors(_data(t)), "types[a].parent", "obrigatório")


def test_parent_missing():
    _has(_errors(_data(_type("a", parent="nada"))), "types[a].parent", "'nada' não existe")


def test_parent_is_annotatable():
    d = _data(_type("a"), _type("b", parent="a"))
    _has(_errors(d), "types[b].parent", "anotável")


def test_cycle_and_depth_in_defense_function():
    _has(check_parent_chain({"a": "b", "b": "a"}), "ciclo")
    _has(check_parent_chain({"a": "b", "b": "c", "c": None}), "profundidade 3")
    assert check_parent_chain({"a": "fam", "fam": None}) == []


def test_symmetric_with_inverse():
    d = _data(_type("a", symmetric=True, inverse_of={"id": "x", "label": "x"}))
    _has(_errors(d), "types[a].inverse_of", "simétrico")


def test_asymmetric_without_inverse():
    t = _type("a")
    del t["inverse_of"]
    _has(_errors(_data(t)), "types[a].inverse_of", "obrigatório")


def test_disjoint_not_reciprocal_names_missing_side():
    d = _data(_type("a", disjoint_with=["b"]), _type("b", symmetric=True))
    _has(_errors(d), "types[a].disjoint_with", "'b'", "falta 'a' em types[b]")


def test_disjoint_self_and_abstract_and_unknown():
    d = _data(_type("a", disjoint_with=["a", "fam", "zzz"]))
    e = _errors(d)
    _has(e, "próprio tipo")
    _has(e, "'fam' é tipo abstrato")
    _has(e, "'zzz' não existe")


def test_domain_outside_parent_domain():
    t = _type("a", domain=["pessoa", "lugar"])
    _has(_errors(_data(t)), "types[a].domain", "fora do domain do pai")


def test_wikidata_mapping_format():
    t = _type("a", mappings={"wikidata": "Q5"})
    _has(_errors(_data(t)), "mappings.wikidata", "'Q5'")


def test_obsolete_without_replaced_by():
    _has(_errors(_data(_type("a", status="obsolete"))), "replaced_by", "obrigatório")


def test_obsolete_with_replacement_ok():
    d = _data(_type("a", status="obsolete", replaced_by=["b"]), _type("b"))
    onto = build_ontology(d)
    assert [t.id for t in onto.annotatable()] == ["b"]
    assert len(onto.relation_types()) == 2


def test_replaced_by_obsolete_target_rejected():
    d = _data(
        _type("a", status="obsolete", replaced_by=["b"]),
        _type("b", status="obsolete", replaced_by=["a"]),
    )
    _has(_errors(d), "não está ativo")


def test_all_errors_in_one_exception():
    d = _data(_type("a", parent="nada", domain=["pessoa"], mappings={"wikidata": "Q5"}))
    del d["types"][0]["inverse_of"]
    e = _errors(d)
    assert len(e) >= 3
    _has(e, "parent")
    _has(e, "inverse_of")
    _has(e, "wikidata")


# ── consultas ────────────────────────────────────────────────────────────────


def test_canonicalize():
    onto = load_ontology(REAL)
    assert onto.canonicalize("progenitor_de", "A", "B") == ("progenitor_de", "A", "B")
    assert onto.canonicalize("filho_de", "B", "A") == ("progenitor_de", "A", "B")
    with pytest.raises(AbstractTypeError):
        onto.canonicalize("relacao_familiar", "A", "B")
    with pytest.raises(OntologyLookupError):
        onto.canonicalize("nao_existe", "A", "B")


def test_ancestors_and_family():
    onto = load_ontology(REAL)
    assert onto.ancestors("vigia") == ["relacao_de_poder"]
    assert onto.ancestors("relacao_de_poder") == []
    assert set(onto.family("vigia")) == {
        "superior_hierarquico_de",
        "exerce_coercao_sobre",
        "vigia",
    }
    assert onto.family("relacao_de_poder") == onto.family("vigia")


def test_disjoint_conflicts():
    onto = load_ontology(REAL)
    hit = onto.disjoint_conflicts([_claim("A", "conjuge_de", "B"), _claim("B", "parente_de", "A")])
    assert len(hit) == 1
    assert (
        onto.disjoint_conflicts([_claim("A", "conjuge_de", "B"), _claim("A", "parente_de", "C")])
        == []
    )
    assert (
        onto.disjoint_conflicts(
            [_claim("A", "amizade_com", "B"), _claim("A", "adversario_de", "B")]
        )
        == []
    )


# ── trava ────────────────────────────────────────────────────────────────────


def _lock(data):
    return update_lock(build_ontology(data), None)


def test_lock_removed_id_fails():
    lock = _lock(_data())
    with pytest.raises(OntologyError) as e:
        update_lock(build_ontology(_data(_type("a"))), lock)
    _has(e.value.errors, "lock[b]", "sumiu")


def test_lock_removed_inverse_view_fails():
    lock = _lock(_data())
    d = _data(_type("a", symmetric=True), _type("b", symmetric=True))
    with pytest.raises(OntologyError) as e:
        update_lock(build_ontology(d), lock)
    _has(e.value.errors, "lock[a_inv]", "sumiu")


def test_lock_semantic_change_fails():
    lock = _lock(_data())
    d = _data()
    d["types"][0]["definition"] = "outra"
    d["types"][0]["version"] = 2
    with pytest.raises(OntologyError) as e:
        update_lock(build_ontology(d), lock)
    _has(e.value.errors, "lock[a]", "semântico")


def test_lock_label_change_needs_version_bump():
    lock = _lock(_data())
    d = _data()
    d["types"][0]["label"] = "novo"
    with pytest.raises(OntologyError) as e:
        update_lock(build_ontology(d), lock)
    _has(e.value.errors, "lock[a]", "sem subir version")
    d["types"][0]["version"] = 2
    new = update_lock(build_ontology(d), lock)
    assert new["ids"]["a"]["version"] == 2


def test_lock_obsolescence_with_replacement_passes_and_cannot_revert():
    base = _data(_type("a"), _type("b"))
    lock = _lock(base)
    obs = copy.deepcopy(base)
    obs["types"][0].update(status="obsolete", replaced_by=["b"])
    lock2 = update_lock(build_ontology(obs), lock)
    assert lock2["ids"]["a"]["status"] == "obsolete"
    with pytest.raises(OntologyError) as e:
        update_lock(build_ontology(base), lock2)
    _has(e.value.errors, "lock[a]", "voltou a active")


def test_lock_adds_new_ids_only():
    lock = _lock(_data(_type("a")))
    new = update_lock(build_ontology(_data(_type("a"), _type("c"))), lock)
    assert set(lock["ids"]) < set(new["ids"])


# ── geração ──────────────────────────────────────────────────────────────────


def test_generated_files_are_current():
    for path, content in render_all().items():
        assert path.read_text(encoding="utf-8") == content, f"desatualizado: {path.name}"


def test_relation_types_json_valid_against_model():
    onto = load_ontology(REAL)
    items = json.loads(render_all()[REAL.parent / "relation-types.json"])
    assert len(items) == 12
    ids = set()
    for raw in items:
        rt = RelationType.model_validate(raw)
        assert isinstance(rt.version, int)
        assert rt.symmetric == onto.get(rt.id).symmetric  # type: ignore[union-attr]
        ids.add(rt.id)
    assert not ids & {a.id for a in onto.file.abstract_types}

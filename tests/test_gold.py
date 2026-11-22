"""Gabarito (B02 §3) e âncora (§4): uma regra de validação por teste.

O texto é sintético; nenhum trecho de obra protegida entra aqui.
"""

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from map_relations.core.ontology import build_ontology
from map_relations.evaluation.gold import (
    Anchor,
    GoldFile,
    GoldRelation,
    check_anchor,
    load_gold,
    relation_id,
    validate_gold,
)
from map_relations.ontology_io import load_ontology
from scripts.generate_schemas import EXTRA_SCHEMAS, SCHEMAS_DIR, render

ONTOLOGY = load_ontology()

# Dois capítulos; "a chave velha" aparece duas vezes (uma por capítulo).
CH1 = "Ana vigiava Bruno todos os dias. A chave velha estava na gaveta.\n\n"
CH2 = "Carla disse que Ana vigiava Bruno. A chave velha sumiu de novo.\n"
TEXT = CH1 + CH2
HASH = "a" * 64


@dataclass
class _Src:
    content_hash: str


@dataclass
class _Par:
    chapter: int | None


class FakeCanonical:
    def __init__(self, text: str = TEXT, content_hash: str = HASH) -> None:
        self.text = text
        self.source = _Src(content_hash)

    def paragraph_at(self, offset: int) -> _Par:
        return _Par(1 if offset < len(CH1) else 2)


def anchor(exact: str, *, nth: int = 0, ctx: int = 32, text: str = TEXT) -> dict:
    """Âncora com contexto de `ctx` code points, da `nth`-ésima ocorrência de `exact`."""
    start = -1
    for _ in range(nth + 1):
        start = text.index(exact, start + 1)
    end = start + len(exact)
    return {
        "exact": exact,
        "prefix": text[max(0, start - ctx) : start],
        "suffix": text[end : end + ctx],
        "startOffset": start,
        "endOffset": end,
    }


def derive_id(rel: dict, ontology=ONTOLOGY) -> str:
    """Id que a relação deve ter (a validação estrutural pede um id qualquer)."""
    return relation_id(GoldRelation.model_validate({**rel, "id": "x"}), ontology)


def make_gold(**over) -> dict:
    data: dict[str, Any] = {
        "schema_version": 1,
        "work": "Obra Sintética",
        "source": {
            "content_hash": "sha256:" + HASH,
            "offset_unit": "codepoint_nfc",
            "end": "exclusive",
        },
        "ontology_version": ONTOLOGY.version,
        "scope": {"chapters": ["1", "2"], "narrative_scopes_evaluated": ["obra"]},
        "annotation_rules": ["regra de teste"],
        "entities": [
            {"id": "ana", "preferredName": "Ana", "aliases": ["a vizinha"]},
            {"id": "bruno", "preferredName": "Bruno"},
            {"id": "carla", "preferredName": "Carla"},
        ],
        "relations": [
            {
                "subject": "ana",
                "type": "exerce_vigilancia_sobre",
                "object": "bruno",
                "class": "afirmada",
                "narrative_scope": "obra",
                "origin": "humano",
                "evidence": [anchor("Ana vigiava Bruno todos os dias")],
            }
        ],
        "negative_pairs": [],
    }
    data.update(over)
    for rel in data["relations"]:
        rel.setdefault("id", derive_id(rel))
    return data


def validate(data: dict, canonical: FakeCanonical | None = FakeCanonical(), ontology=ONTOLOGY):
    return validate_gold(GoldFile.model_validate(data), ontology, canonical)


def errors(data: dict, **kw) -> list[str]:
    return validate(data, **kw).errors


def only_relation(data: dict) -> dict:
    return data["relations"][0]


# ── caso válido ───────────────────────────────────────────────────────────────


def test_valid_gold_has_no_errors_or_warnings():
    rep = validate(make_gold())
    assert rep.errors == []
    assert rep.warnings == []
    assert rep.ok


def test_load_gold_reads_file(tmp_path: Path):
    path = tmp_path / "g.json"
    path.write_text(json.dumps(make_gold()), encoding="utf-8")
    assert load_gold(path).work == "Obra Sintética"


def test_without_canonical_warns_that_anchors_were_not_checked():
    rep = validate(make_gold(), canonical=None)
    assert rep.errors == []
    assert any("sem canônico" in w for w in rep.warnings)


# ── regras do §3, uma por teste ───────────────────────────────────────────────


def test_unknown_type_is_error():
    d = make_gold()
    only_relation(d)["type"] = "inventado"
    d["relations"][0]["id"] = "r_x"
    assert any("não existe na ontologia" in e for e in errors(d))


def test_abstract_type_is_error():
    d = make_gold()
    only_relation(d)["type"] = "relacao_de_poder"
    assert any("abstrato" in e for e in errors(d))


def test_obsolete_type_is_error():
    raw = ONTOLOGY.to_dict()
    for t in raw["types"]:
        if t["id"] == "adversario_de":
            t["status"] = "obsolete"
            t["replaced_by"] = ["amizade_com"]
    onto = build_ontology(raw)
    d = make_gold()
    only_relation(d)["type"] = "adversario_de"
    only_relation(d)["id"] = derive_id(only_relation(d), onto)
    assert any("obsoleto" in e for e in errors(d, ontology=onto))


def test_inverse_view_is_accepted_and_normalized():
    d = make_gold()
    rel = only_relation(d)
    rel["subject"], rel["object"], rel["type"] = "bruno", "ana", "vigiado_por"
    # mesmo id que a forma canônica: a inversa é só visão de consulta
    assert rel["id"] == derive_id(rel)
    assert errors(d) == []


def test_unknown_class_is_rejected_by_model():
    d = make_gold()
    only_relation(d)["class"] = "palpite"
    with pytest.raises(ValidationError):
        GoldFile.model_validate(d)


def test_alegada_requires_asserted_by():
    d = make_gold()
    only_relation(d)["class"] = "alegada"
    with pytest.raises(ValidationError, match="exige asserted_by"):
        GoldFile.model_validate(d)


def test_asserted_by_only_with_alegada():
    d = make_gold()
    only_relation(d)["asserted_by"] = "carla"
    with pytest.raises(ValidationError, match="só é permitido"):
        GoldFile.model_validate(d)


def test_asserted_by_must_be_a_known_entity():
    d = make_gold()
    rel = only_relation(d)
    rel["class"], rel["asserted_by"] = "alegada", "ninguem"
    rel["id"] = derive_id(rel)
    assert any("'ninguem' não existe" in e for e in errors(d))


def test_alegada_with_known_asserted_by_is_valid():
    d = make_gold()
    rel = only_relation(d)
    rel["class"], rel["asserted_by"] = "alegada", "carla"
    rel["evidence"] = [anchor("Carla disse que Ana vigiava Bruno")]
    rel["id"] = derive_id(rel)
    assert errors(d) == []


def test_narrative_scope_is_required():
    d = make_gold()
    del only_relation(d)["narrative_scope"]
    with pytest.raises(ValidationError, match="narrative_scope"):
        GoldFile.model_validate(d)


def test_narrative_scope_must_be_known():
    d = make_gold()
    only_relation(d)["narrative_scope"] = "sonho"
    with pytest.raises(ValidationError):
        GoldFile.model_validate(d)


def test_origin_must_be_known():
    d = make_gold()
    only_relation(d)["origin"] = "adivinhacao"
    with pytest.raises(ValidationError):
        GoldFile.model_validate(d)


@pytest.mark.parametrize("origin", ["modelo", "modelo_revisado"])
def test_model_origins_require_origin_detail_model(origin):
    d = make_gold()
    only_relation(d)["origin"] = origin
    with pytest.raises(ValidationError, match="origin_detail.model"):
        GoldFile.model_validate(d)
    only_relation(d)["origin_detail"] = {"model": "modelo-x"}
    GoldFile.model_validate(d)


def test_human_origin_needs_no_detail():
    GoldFile.model_validate(make_gold())


def test_reflexive_relation_in_irreflexive_type_is_error():
    d = make_gold()
    rel = only_relation(d)
    rel["object"] = "ana"
    rel["id"] = derive_id(rel)
    assert any("sujeito igual ao objeto" in e for e in errors(d))


def test_disjunction_is_warning_not_error():
    d = make_gold()
    d["relations"] = [
        {
            "subject": "ana",
            "type": "parente_de",
            "object": "bruno",
            "class": "afirmada",
            "narrative_scope": "obra",
            "origin": "humano",
            "evidence": [anchor("Ana vigiava Bruno todos os dias")],
        },
        {
            "subject": "ana",
            "type": "conjuge_de",
            "object": "bruno",
            "class": "afirmada",
            "narrative_scope": "obra",
            "origin": "humano",
            "evidence": [anchor("A chave velha estava na gaveta")],
        },
    ]
    d = make_gold(**{k: v for k, v in d.items()})
    rep = validate(d)
    assert rep.errors == []
    assert any("disjunção" in w for w in rep.warnings)


def test_duplicate_claim_key_is_error():
    d = make_gold()
    dup = copy.deepcopy(only_relation(d))
    dup["evidence"] = [anchor("A chave velha estava na gaveta")]
    d["relations"].append(dup)
    assert any("duplica a relação" in e for e in errors(d))


def test_duplicate_claim_key_sees_symmetry_from_the_type():
    d = make_gold()
    d["relations"] = []
    for s, o, quote in (("ana", "bruno", "Ana vigiava Bruno todos os dias"),
                        ("bruno", "ana", "A chave velha estava na gaveta")):
        d["relations"].append(
            {
                "subject": s,
                "type": "amizade_com",
                "object": o,
                "class": "afirmada",
                "narrative_scope": "obra",
                "origin": "humano",
                "evidence": [anchor(quote)],
            }
        )
    d = make_gold(relations=d["relations"])
    assert any("duplica a relação" in e for e in errors(d))


def test_same_pair_with_other_scope_or_asserter_is_not_duplicate():
    d = make_gold()
    other = copy.deepcopy(only_relation(d))
    other["narrative_scope"] = "texto_encaixado"
    del other["id"]
    d["relations"].append(other)
    d = make_gold(relations=d["relations"])
    assert errors(d) == []


def test_relation_id_must_match_derived_id():
    d = make_gold()
    only_relation(d)["id"] = "r_errado"
    assert any("id deveria ser" in e for e in errors(d))


def test_relation_id_is_stable_and_short():
    rid = only_relation(make_gold())["id"]
    assert rid.startswith("r_") and len(rid) == 14


def test_ontology_version_mismatch_is_error():
    d = make_gold(ontology_version=99)
    assert any("ontology_version" in e for e in errors(d))


def test_relation_with_unknown_entity_is_error():
    d = make_gold()
    rel = only_relation(d)
    rel["object"] = "fantasma"
    rel["id"] = "r_x"
    assert any("'fantasma' não existe" in e for e in errors(d))


def test_duplicate_entity_id_is_error():
    d = make_gold()
    d["entities"].append({"id": "ana", "preferredName": "Outra Ana"})
    assert any("id repetido 'ana'" in e for e in errors(d))


def test_relation_without_evidence_is_rejected():
    d = make_gold()
    only_relation(d)["evidence"] = []
    with pytest.raises(ValidationError):
        GoldFile.model_validate(d)


def test_unknown_field_is_rejected():
    d = make_gold()
    only_relation(d)["chapter"] = "1"  # o capítulo é derivado, nunca gravado
    with pytest.raises(ValidationError):
        GoldFile.model_validate(d)


# ── canônico: hash, âncoras e pares de controle ───────────────────────────────


def test_hash_different_from_canonical_asks_for_fill_offsets():
    errs = errors(make_gold(), canonical=FakeCanonical(content_hash="b" * 64))
    assert len(errs) == 1 and "rode fill-offsets" in errs[0]


def test_content_hash_format_is_checked():
    d = make_gold()
    d["source"]["content_hash"] = "46a0"
    with pytest.raises(ValidationError):
        GoldFile.model_validate(d)


def test_anchor_off_by_one_is_error():
    d = make_gold()
    a = only_relation(d)["evidence"][0]
    a["startOffset"] += 1
    a["endOffset"] += 1
    assert any("text[startOffset:endOffset] ≠ exact" in e for e in errors(d))


def test_anchor_with_wrong_prefix_or_suffix_is_error():
    d = make_gold()
    only_relation(d)["evidence"][0]["prefix"] = "XX"
    assert any("prefix não confere" in e for e in errors(d))
    d = make_gold()
    only_relation(d)["evidence"][0]["suffix"] = "XX"
    assert any("suffix não confere" in e for e in errors(d))


def test_fictional_relation_is_not_checked_against_canonical():
    d = make_gold()
    rel = only_relation(d)
    rel["fictional"] = True
    rel["evidence"][0]["startOffset"] += 5
    rel["evidence"][0]["endOffset"] += 5
    assert errors(d) == []


def test_negative_pair_inside_same_chapter_as_relation_is_error():
    d = make_gold(
        negative_pairs=[
            {"subject": "bruno", "object": "ana", "chapters": ["1"], "expected": "sem_relacao"}
        ]
    )
    assert any("par de controle" in e and "['1']" in e for e in errors(d))


def test_negative_pair_in_other_chapter_is_fine():
    d = make_gold(
        negative_pairs=[
            {"subject": "ana", "object": "bruno", "chapters": ["2"], "expected": "sem_relacao"}
        ]
    )
    assert errors(d) == []


def test_negative_pair_with_unknown_entity_is_error():
    d = make_gold(
        negative_pairs=[
            {"subject": "ana", "object": "fantasma", "chapters": ["1"], "expected": "sem_relacao"}
        ]
    )
    assert any("'fantasma' não existe" in e for e in errors(d))


def test_negative_pair_expected_must_be_sem_relacao():
    d = make_gold(
        negative_pairs=[
            {"subject": "ana", "object": "carla", "chapters": ["1"], "expected": "nenhuma"}
        ]
    )
    with pytest.raises(ValidationError):
        GoldFile.model_validate(d)


# ── âncora (§4) ───────────────────────────────────────────────────────────────


def test_anchor_span_must_match_exact_length():
    a = anchor("Ana vigiava")
    a["endOffset"] += 1
    with pytest.raises(ValidationError, match=r"len\(exact\)"):
        Anchor.model_validate(a)


def test_anchor_offsets_must_be_non_negative_and_ordered():
    a = anchor("Ana vigiava")
    a["startOffset"], a["endOffset"] = -1, 10
    with pytest.raises(ValidationError):
        Anchor.model_validate(a)


def test_anchor_requires_all_five_fields():
    a = anchor("Ana vigiava")
    del a["prefix"]
    with pytest.raises(ValidationError):
        Anchor.model_validate(a)


def test_anchor_accepts_python_names_too():
    a = anchor("Ana vigiava")
    py = {"exact": a["exact"], "prefix": a["prefix"], "suffix": a["suffix"],
          "start_offset": a["startOffset"], "end_offset": a["endOffset"]}
    assert Anchor.model_validate(py).start_offset == a["startOffset"]


def test_unique_quote_is_valid_with_context_cut_at_text_edges():
    a = Anchor.model_validate(anchor("Ana vigiava Bruno todos os dias"))
    assert a.prefix == ""  # início do texto
    assert check_anchor(a, TEXT) == []
    last = Anchor.model_validate(anchor("sumiu de novo.\n"))
    assert last.suffix == ""  # fim do texto
    assert check_anchor(last, TEXT) == []


def test_repeated_quote_needs_context_to_be_unique():
    bare = Anchor.model_validate(anchor("A chave velha", ctx=0))
    assert any("não é única" in e for e in check_anchor(bare, TEXT))
    for nth in (0, 1):
        ctx = Anchor.model_validate(anchor("A chave velha", nth=nth, ctx=12))
        assert check_anchor(ctx, TEXT) == []


def test_anchor_points_at_the_requested_occurrence():
    first = Anchor.model_validate(anchor("A chave velha", nth=0, ctx=12))
    second = Anchor.model_validate(anchor("A chave velha", nth=1, ctx=12))
    assert first.start_offset < len(CH1) <= second.start_offset


def test_anchor_beyond_text_is_error():
    a = Anchor.model_validate(anchor("sumiu de novo."))
    short = TEXT[:-30]
    assert check_anchor(a, short) == [f"offset {a.end_offset} além do fim do texto ({len(short)})"]


def test_anchor_counts_code_points_not_bytes_or_utf16():
    text = "ação 😀 café é bom. Outra frase."
    a = Anchor.model_validate(anchor("café é bom", ctx=6, text=text))
    assert a.start_offset == text.index("café")  # code points
    assert check_anchor(a, text) == []


# ── schema gerado ─────────────────────────────────────────────────────────────


def test_gold_schema_file_matches_model():
    for name, model in EXTRA_SCHEMAS.items():
        path = SCHEMAS_DIR / name
        assert path.exists(), f"faltando: {name} — rode make schema"
        assert path.read_text(encoding="utf-8") == render(model), f"desatualizado: {name}"


def test_gold_schema_uses_documented_field_names():
    text = (SCHEMAS_DIR / "gold.schema.json").read_text(encoding="utf-8")
    for name in ("startOffset", "endOffset", "preferredName", "asserted_by", "narrative_scope"):
        assert f'"{name}"' in text
    for hidden in ("start_offset", "end_offset", "preferred_name", "class_", "type_", "object_"):
        assert f'"{hidden}"' not in text


def test_gold_schema_validates_a_valid_gold_shape():
    schema = json.loads((SCHEMAS_DIR / "gold.schema.json").read_text(encoding="utf-8"))
    assert set(schema["required"]) >= {"schema_version", "work", "source", "relations"}

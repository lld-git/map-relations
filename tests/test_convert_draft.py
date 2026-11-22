"""Conversão do rascunho legado (B02 §6) sobre um rascunho sintético."""

import copy
import json
from pathlib import Path

from map_relations.__main__ import main
from map_relations.evaluation.convert_draft import convert_draft, parse_chapters, slugify
from map_relations.evaluation.gold import GoldFile, validate_gold
from map_relations.ontology_io import load_ontology
from tests.gold_helpers import make_canon, write_processed

CANON = make_canon()
ONTO = load_ontology()


def draft() -> dict:
    return {
        "work": "Sintética",
        "edition": "x",
        "sourceContentHash": "sha256:" + "0" * 64,
        "normalization": {"form": "NFC"},
        "scope": {"chapters": ["1", "2"], "relation_types_source": "ontology.yaml v1.0.0"},
        "rules": ["regra A", "regra B"],
        "entities": [
            {"preferredName": "Ana", "aliases": ["a vizinha"]},
            {"preferredName": "Bruno", "aliases": []},
            {"preferredName": "Carla Éster", "aliases": []},
        ],
        "relations": [
            {
                "subject": "Ana", "type": "vigia", "object": "Bruno", "class": "afirmada",
                "chapter": "1", "startOffset": 5, "endOffset": 9, "quote": "Ana vigiava Bruno",
                "asserted_by": None, "origin": "modelo",
                "occurrences_in_text": 1, "occurrence_used": 1,
            },
            {
                "subject": "a vizinha", "type": "exerce_vigilancia_sobre", "object": "Bruno",
                "class": "alegada", "chapter": "2", "startOffset": 1, "endOffset": 2,
                "quote": "Bruno respondeu que", "asserted_by": "Carla Éster", "origin": "modelo",
                "occurrences_in_text": 1, "occurrence_used": 1,
            },
        ],
        "negative_pairs": [
            {"subject": "Bruno", "object": "Carla Éster", "scope": "capítulos 1-2",
             "expected": "nenhuma relação de nenhum tipo"},
        ],
    }


def convert(d: dict):
    return convert_draft(d, CANON, ONTO)


def test_slug_and_chapters_parsing():
    assert slugify("Carla Éster") == "carla_ester" and slugify("Josef K.") == "josef_k"
    assert parse_chapters("capítulos 1-3") == ["1", "2", "3"]
    assert parse_chapters("capítulo 2") == ["2"]
    assert parse_chapters("capítulos 1, 3 e 5") == ["1", "3", "5"]
    assert parse_chapters("tudo") is None and parse_chapters("capítulos 3-1") is None


def test_full_conversion_is_valid_against_ontology_and_canonical():
    new, rep = convert(draft())
    assert rep.ok and new is not None
    assert (rep.converted, rep.failed) == (2, 0)
    gold = GoldFile.model_validate(new)
    assert validate_gold(gold, ONTO, CANON).ok
    r0, r1 = gold.relations
    assert r0.type_ == "exerce_vigilancia_sobre"  # tabela fixa vigia → …
    assert (r0.subject, r0.object_) == ("ana", "bruno")
    assert r1.asserted_by == "carla_ester" and r1.class_.value == "alegada"
    assert r0.narrative_scope.value == "obra" and r0.origin.value == "modelo"
    assert r0.origin_detail and r0.origin_detail.model == "desconhecido"
    assert rep.narrative_scope_defaulted == 2
    assert gold.negative_pairs[0].chapters == ["1", "2"]
    assert gold.negative_pairs[0].expected.value == "sem_relacao"
    assert gold.ontology_version == ONTO.version and gold.annotation_rules == ["regra A", "regra B"]


def test_old_offsets_are_discarded():
    new, _ = convert(draft())
    ev = new["relations"][0]["evidence"][0]
    assert ev["startOffset"] == CANON.text.index("Ana vigiava Bruno")  # não o 5 do rascunho
    assert "occurrences_in_text" not in new["relations"][0]


def test_draft_is_not_modified():
    d = draft()
    snapshot = copy.deepcopy(d)
    convert(d)
    assert d == snapshot


def test_inverse_view_is_normalized_by_canonicalize():
    d = draft()
    d["relations"][0].update(type="subordinado_a", subject="Ana", object="Bruno")
    new, rep = convert(d)
    assert rep.ok
    r = new["relations"][0]
    assert (r["type"], r["subject"], r["object"]) == ("superior_hierarquico_de", "bruno", "ana")


def test_ambiguous_quote_is_error_with_words_and_reference_only():
    d = draft()
    d["relations"][0].update(quote="a chave velha", occurrences_in_text=3, occurrence_used=1)
    new, rep = convert(d)
    assert new is None and (rep.converted, rep.failed) == (1, 1)
    [dec] = rep.decisions
    assert len(dec.ambiguous) == 3
    first = dec.ambiguous[0]
    assert first["draft_used"] and first["where"] == "cap. 1, § 2"
    assert first["before"].endswith("Carla disse que") and first["after"].startswith("estava na")
    text = rep.render() + json.dumps(rep.to_json(), ensure_ascii=False)
    assert "chave velha" not in text  # a citação nunca é impressa


def test_hand_prefix_resolves_the_ambiguity():
    d = draft()
    i = CANON.text.index("a chave velha sumiu")
    d["relations"][0].update(quote="a chave velha", prefix=CANON.text[i - 12 : i], chapter="2")
    new, rep = convert(d)
    assert rep.ok and new["relations"][0]["evidence"][0]["startOffset"] == i


def test_quote_not_found_is_error():
    d = draft()
    d["relations"][0]["quote"] = "frase que não existe"
    new, rep = convert(d)
    assert new is None and "nao_encontrada" in rep.relations[0].errors[0]


def test_chapter_mismatch_is_error():
    d = draft()
    d["relations"][0]["chapter"] = "2"
    new, rep = convert(d)
    assert new is None and "capítulo do rascunho (2)" in rep.relations[0].errors[0]


def test_unknown_or_ambiguous_names_are_errors():
    d = draft()
    d["relations"][0]["subject"] = "Fulano"
    d["entities"][1]["aliases"] = ["a vizinha"]  # alias repetido em duas entidades
    new, rep = convert(d)
    assert new is None
    msgs = " ".join(e for r in rep.relations for e in r.errors)
    assert "'Fulano': nenhuma entidade casa" in msgs and "'a vizinha': casa com 2" in msgs


def test_slug_collision_is_error():
    d = draft()
    d["entities"].append({"preferredName": "ANA", "aliases": []})
    new, rep = convert(d)
    assert new is None and any("mesmo id 'ana'" in e for e in rep.errors)


def test_unknown_type_and_bad_class_are_errors():
    d = draft()
    d["relations"][0].update(type="tipo_inventado", **{"class": "talvez"})
    new, rep = convert(d)
    assert new is None
    assert len(rep.relations[0].errors) == 2


def test_alegada_without_asserted_by_is_error():
    d = draft()
    d["relations"][1]["asserted_by"] = None
    new, rep = convert(d)
    assert new is None and rep.failed == 1


def test_negative_pair_scope_not_understood_is_error():
    d = draft()
    d["negative_pairs"][0]["scope"] = "o livro todo"
    new, rep = convert(d)
    assert new is None and any("escopo" in e for e in rep.errors)


def test_cli_converts_and_is_all_or_nothing(tmp_path: Path):
    canon = write_processed(tmp_path, CANON)
    src, out = tmp_path / "draft.json", tmp_path / "out.json"
    src.write_text(json.dumps(draft()), encoding="utf-8")
    args = ["gold", "convert-draft", "--draft", str(src), "--canonical", str(canon),
            "--out", str(out)]
    assert main(args) == 0 and GoldFile.model_validate_json(out.read_text())
    out.unlink()
    bad = draft()
    bad["relations"][0]["quote"] = "a chave velha"
    src.write_text(json.dumps(bad), encoding="utf-8")
    assert main(args) == 1 and not out.exists()


def test_cli_refuses_out_equal_to_draft(tmp_path: Path):
    canon = write_processed(tmp_path, CANON)
    src = tmp_path / "draft.json"
    src.write_text(json.dumps(draft()), encoding="utf-8")
    code = main(["gold", "convert-draft", "--draft", str(src), "--canonical", str(canon),
                 "--out", str(src)])
    assert code == 2 and json.loads(src.read_text()) == draft()


def test_cli_validate_reports_stale_hash(tmp_path: Path, capsys):
    canon = write_processed(tmp_path, CANON)
    new, _ = convert(draft())
    new["source"]["content_hash"] = "sha256:" + "1" * 64
    g = tmp_path / "g.json"
    g.write_text(json.dumps(new), encoding="utf-8")
    assert main(["gold", "validate", "--gold", str(g), "--canonical", str(canon)]) == 1
    assert "rode fill-offsets" in capsys.readouterr().out

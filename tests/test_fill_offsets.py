"""Âncora e fill-offsets (B02 §4 e §5): um teste por caso listado no §11, fase 2."""

import json
from pathlib import Path

import pytest

from map_relations.__main__ import main
from map_relations.evaluation.anchoring import (
    AnchorError,
    AnchorErrorKind,
    AnchorInput,
    AnchorResolved,
    build_context,
    find_occurrences,
    resolve_anchor,
    words_around,
)
from map_relations.evaluation.fill_offsets import (
    CanonicalError,
    default_canonical,
    fill_offsets,
    load_canonical,
)
from map_relations.evaluation.gold import GoldFile, check_anchor
from tests.gold_helpers import COMMON, make_canon, write_processed

CANON = make_canon()
TEXT = CANON.text
HASH = CANON.source.content_hash


def gold_with(*evidence: dict, extra_relations: list[dict] | None = None) -> dict:
    rels = [
        {
            "id": f"r{i}",
            "subject": "ana",
            "type": "exerce_vigilancia_sobre",
            "object": "bruno",
            "class": "afirmada",
            "narrative_scope": "obra",
            "origin": "humano",
            "evidence": [ev],
        }
        for i, ev in enumerate(evidence)
    ]
    return {
        "schema_version": 1,
        "work": "Sintética",
        "source": {
            "content_hash": "sha256:" + "0" * 64,
            "offset_unit": "codepoint_nfc",
            "end": "exclusive",
        },
        "ontology_version": 1,
        "scope": {"chapters": ["1", "2"], "narrative_scopes_evaluated": ["obra"]},
        "entities": [
            {"id": "ana", "preferredName": "Ana"},
            {"id": "bruno", "preferredName": "Bruno"},
        ],
        "relations": rels + (extra_relations or []),
        "negative_pairs": [],
    }


def only(exact: str, **kw) -> AnchorResolved:
    res = resolve_anchor(TEXT, AnchorInput(exact=exact, **kw))
    assert isinstance(res, AnchorResolved), res
    return res


# ── resolve_anchor ────────────────────────────────────────────────────────────


def test_unique_exact_is_accepted_and_anchor_is_valid():
    res = only("Ana vigiava Bruno")
    a = res.anchor
    assert TEXT[a.start_offset : a.end_offset] == "Ana vigiava Bruno"
    assert check_anchor(a, TEXT) == []
    assert res.filled and not res.moved  # modo âncora mínima


def test_unchanged_when_position_and_context_already_right():
    first = only("Ana vigiava Bruno").anchor
    again = only(
        "Ana vigiava Bruno",
        prefix=first.prefix,
        suffix=first.suffix,
        startOffset=first.start_offset,
        endOffset=first.end_offset,
    )
    assert again.unchanged


def test_unique_with_changed_context_is_warning_not_error():
    first = only("Ana vigiava Bruno").anchor
    res = only(
        "Ana vigiava Bruno",
        prefix="contexto velho",
        suffix="também velho",
        startOffset=first.start_offset,
        endOffset=first.end_offset,
    )
    assert res.context_updated and not res.moved
    assert res.anchor.suffix == first.suffix  # contexto regravado


def test_unique_with_new_position_is_moved_and_old_offset_is_only_info():
    res = only("Ana vigiava Bruno", startOffset=999, endOffset=999 + 17)
    assert res.moved
    assert (res.old_start, res.anchor.start_offset) == (999, TEXT.index("Ana vigiava"))


def test_repeated_exact_resolved_by_stored_context():
    occs = find_occurrences(TEXT, "a chave velha")
    assert len(occs) == 3
    second = occs[1]
    res = only("a chave velha", prefix=TEXT[second.start - 8 : second.start])
    assert res.anchor.start_offset == second.start


def test_repeated_exact_without_context_is_ambiguous_and_lists_candidates():
    res = resolve_anchor(TEXT, AnchorInput(exact="a chave velha"))
    assert isinstance(res, AnchorError) and res.kind is AnchorErrorKind.ambigua
    assert len(res.candidates) == 3 and res.matching_context == 3


def test_old_offset_never_breaks_a_tie():
    third = find_occurrences(TEXT, "a chave velha")[2]
    res = resolve_anchor(
        TEXT, AnchorInput(exact="a chave velha", startOffset=third.start, endOffset=third.end)
    )
    assert isinstance(res, AnchorError) and res.kind is AnchorErrorKind.ambigua


def test_context_matching_two_candidates_is_still_ambiguous():
    res = resolve_anchor(TEXT, AnchorInput(exact="a chave velha", suffix=" "))
    assert isinstance(res, AnchorError) and res.matching_context == 3


def test_absent_exact_is_not_found_and_approximate_match_is_not_used():
    res = resolve_anchor(TEXT, AnchorInput(exact="Ana vigiava Brunо"))  # о cirílico
    assert isinstance(res, AnchorError) and res.kind is AnchorErrorKind.nao_encontrada


def test_context_grows_until_unique_without_cutting_words():
    start = TEXT.index("CITA")
    res = only("CITA", prefix="alfa " + COMMON)
    a = res.anchor
    assert a.start_offset == start
    assert 32 < len(a.prefix) <= 128 and 32 < len(a.suffix) <= 128
    assert check_anchor(a, TEXT) == []
    assert not (a.prefix[0].isalnum() and TEXT[a.start_offset - len(a.prefix) - 1].isalnum())


def test_context_default_is_32_and_ends_on_word_boundary():
    a = only("Ana vigiava Bruno").anchor
    assert len(a.prefix) <= 32 and len(a.suffix) <= 32
    after = TEXT[a.end_offset + len(a.suffix)]
    assert a.suffix == "" or not (a.suffix[-1].isalnum() and after.isalnum())


def test_build_context_gives_up_past_the_limit():
    start = TEXT.index("CITA")
    assert build_context(TEXT, start, start + 4, limit=48) is None


def test_words_around_returns_only_neighbours():
    i = TEXT.index("gaveta")
    par = CANON.paragraph_at(i)
    before, after = words_around(TEXT, i, i + 6, (par.start_offset, par.end_offset), words=2)
    assert (before, after) == ("estava na", ". Depois")


# ── fill_offsets ──────────────────────────────────────────────────────────────


def test_fill_minimal_anchor_updates_hash_and_validates():
    data = gold_with({"exact": "Ana vigiava Bruno"})
    new, rep = fill_offsets(data, CANON)
    assert rep.ok and new is not None
    assert new["source"]["content_hash"] == "sha256:" + HASH
    GoldFile.model_validate(new)
    assert rep.counts() == {"preenchida": 1}
    assert rep.outcomes[0].where == "cap. 1, § 1"


def test_input_is_never_modified():
    data = gold_with({"exact": "Ana vigiava Bruno"})
    snapshot = json.dumps(data)
    fill_offsets(data, CANON)
    assert json.dumps(data) == snapshot


def test_all_or_nothing_on_any_error():
    data = gold_with({"exact": "Ana vigiava Bruno"}, {"exact": "a chave velha"})
    new, rep = fill_offsets(data, CANON)
    assert new is None and not rep.ok
    assert rep.counts() == {"preenchida": 1, "erro": 1}
    bad = [o for o in rep.outcomes if o.status == "erro"][0]
    assert len(bad.candidates) == 3 and bad.candidates[0]["where"].startswith("cap. 1")


def test_not_found_is_error():
    new, rep = fill_offsets(gold_with({"exact": "texto que não existe"}), CANON)
    assert new is None and rep.outcomes[0].detail.startswith("nao_encontrada")


def test_fictional_relations_are_left_alone():
    ev = {"exact": "nada disso existe", "prefix": "", "suffix": "",
          "startOffset": 5, "endOffset": 22}
    fic = {**gold_with(ev)["relations"][0], "id": "f", "fictional": True}
    new, rep = fill_offsets(gold_with({"exact": "Ana vigiava Bruno"}, extra_relations=[fic]), CANON)
    assert new is not None and new["relations"][-1]["evidence"][0] == ev


def test_relation_without_evidence_is_error():
    data = gold_with({"exact": "Ana vigiava Bruno"})
    data["relations"][0]["evidence"] = []
    new, rep = fill_offsets(data, CANON)
    assert new is None and "sem evidência" in rep.errors[0]


def test_report_carries_no_quote_text():
    _, rep = fill_offsets(gold_with({"exact": "Ana vigiava Bruno"}), CANON)
    assert "vigiava" not in json.dumps(rep.to_json()) + rep.render_table()


# ── canônico em disco e CLI ───────────────────────────────────────────────────


def test_load_canonical_roundtrip_and_hash_check(tmp_path: Path):
    path = write_processed(tmp_path, CANON)
    assert load_canonical(path).text == TEXT
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(CanonicalError):
        load_canonical(path)


def test_default_canonical_requires_exactly_one(tmp_path: Path):
    with pytest.raises(CanonicalError):
        default_canonical(tmp_path / "processed")
    path = write_processed(tmp_path, CANON)
    assert default_canonical(tmp_path / "processed") == path


def run_cli(
    tmp_path: Path, data: dict, *extra: str, out_name: str = "out.json"
) -> tuple[int, Path, Path]:
    canon = write_processed(tmp_path, CANON)
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / out_name
    code = main(["gold", "fill-offsets", "--gold", str(gold), "--canonical", str(canon),
                 "--out", str(out), *extra])
    return code, gold, out


def test_cli_writes_out_and_leaves_gold_intact(tmp_path: Path, capsys):
    data = gold_with({"exact": "Ana vigiava Bruno"})
    code, gold, out = run_cli(tmp_path, data, "--report", str(tmp_path / "rep.json"))
    assert code == 0 and json.loads(gold.read_text()) == data
    GoldFile.model_validate_json(out.read_text())
    assert json.loads((tmp_path / "rep.json").read_text())["ok"] is True


def test_cli_error_writes_nothing_and_exits_1(tmp_path: Path, capsys):
    code, _, out = run_cli(tmp_path, gold_with({"exact": "a chave velha"}))
    assert code == 1 and not out.exists()


def test_cli_refuses_out_equal_to_gold(tmp_path: Path, capsys):
    data = gold_with({"exact": "Ana vigiava Bruno"})
    code, gold, _ = run_cli(tmp_path, data, out_name="gold.json")
    assert code == 2 and json.loads(gold.read_text()) == data
    assert "--out" in capsys.readouterr().err

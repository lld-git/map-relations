"""Validações dos modelos do core: offsets, confidence, level, aliases camelCase."""

import pytest
from pydantic import ValidationError

from map_relations.core.ids import (
    _hash,
    claim_key,
    evidence_key,
    new_id,
    nfc,
    participation_key,
)
from map_relations.core.models import (
    Alias,
    Claim,
    ClaimClass,
    Entity,
    EntityKind,
    Evidence,
    Mention,
    NarrativeScope,
    Participation,
    Pass,
    PassStopReason,
    RelationType,
    Role,
    Segment,
    TargetType,
)


def _claim(**overrides) -> Claim:
    base = dict(
        claim_key="k",
        subject_id="s",
        type_id="t",
        object_id="o",
        claim_class=ClaimClass.afirmada,
        confidence=0.9,
        pass_id="p",
    )
    base.update(overrides)
    return Claim(**base)


# ── ids e chaves ──────────────────────────────────────────────────────────────


def test_new_id_is_uuid4():
    assert len(new_id()) == 36
    assert new_id() != new_id()


def test_nfc_normalizes_decomposed_text():
    decomposed = "José"  # e + combining acute
    assert nfc(decomposed) == "José"
    assert len(nfc(decomposed)) == 4


def _rt(id_: str = "t", symmetric: bool = False) -> RelationType:
    return RelationType(
        id=id_,
        label=id_,
        definition="d",
        subject_kinds=[EntityKind.pessoa],
        object_kinds=[EntityKind.pessoa],
        version=1,
        symmetric=symmetric,
    )


def test_content_keys_are_deterministic():
    assert claim_key("s", _rt(), "o") == claim_key("s", _rt(), "o")
    assert participation_key("e", "p", "autor") == participation_key("e", "p", "autor")
    assert evidence_key("h", 0, 10) == evidence_key("h", 0, 10)


def test_content_keys_differ_by_component():
    assert claim_key("s", _rt(), "o") != claim_key("o", _rt(), "s")
    assert participation_key("e", "p", "autor") != participation_key("e", "p", "alvo")
    assert evidence_key("h", 0, 10) != evidence_key("h", 0, 11)


def test_claim_key_no_juxtaposition_collision():
    # separador \x00 impede que ("ab","c") colida com ("a","bc")
    assert claim_key("ab", _rt("c"), "x") != claim_key("a", _rt("bc"), "x")


def test_claim_key_symmetric_ab_eq_ba():
    sym = _rt(symmetric=True)
    assert claim_key("A", sym, "B") == claim_key("B", sym, "A")


def test_claim_key_nonsymmetric_ab_neq_ba():
    assert claim_key("A", _rt(), "B") != claim_key("B", _rt(), "A")


def test_claim_key_plain_claim_equals_plain_hash():
    # chave de claim comum continua hash(s, type_id, o), sem asserted_by/escopo
    assert claim_key("s", _rt(), "o") == _hash("s", "t", "o")


def test_claim_key_asserted_by_changes_key():
    assert claim_key("s", _rt(), "o", asserted_by="x") != claim_key("s", _rt(), "o")
    x = claim_key("s", _rt(), "o", asserted_by="x")
    assert x != claim_key("s", _rt(), "o", asserted_by="y")


def test_claim_key_narrative_scope_changes_key():
    assert claim_key("s", _rt(), "o", narrative_scope="texto_encaixado") != claim_key(
        "s", _rt(), "o"
    )


def test_claim_key_ignores_class():
    # a classe não é parâmetro: afirmada e inferida para o mesmo trio têm a mesma chave
    a = _claim(claim_key=claim_key("s", _rt(), "o"), claim_class=ClaimClass.afirmada)
    b = _claim(claim_key=claim_key("s", _rt(), "o"), claim_class=ClaimClass.inferida)
    assert a.claim_key == b.claim_key


# ── claim alegada, asserted_by e narrative_scope ──────────────────────────────


def test_alegada_requires_asserted_by():
    with pytest.raises(ValidationError, match="asserted_by"):
        _claim(claim_class=ClaimClass.alegada)
    assert _claim(claim_class=ClaimClass.alegada, asserted_by="x").asserted_by == "x"


def test_asserted_by_rejected_outside_alegada():
    with pytest.raises(ValidationError, match="asserted_by"):
        _claim(claim_class=ClaimClass.afirmada, asserted_by="x")


def test_narrative_scope_validation():
    assert _claim().narrative_scope is None
    nested = _claim(narrative_scope="texto_encaixado")
    assert nested.narrative_scope is NarrativeScope.texto_encaixado
    with pytest.raises(ValidationError):
        _claim(narrative_scope="sonho")


# ── offsets ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("start,end", [(0, 1), (5, 100)])
def test_valid_offsets(start: int, end: int):
    m = Mention(entity_id="e", segment_id="s", start_offset=start, end_offset=end, surface="x")
    assert m.start_offset == start


@pytest.mark.parametrize("start,end", [(5, 5), (10, 3), (-1, 5), (0, -2)])
def test_invalid_offsets_rejected(start: int, end: int):
    with pytest.raises(ValidationError):
        Mention(entity_id="e", segment_id="s", start_offset=start, end_offset=end, surface="x")
    with pytest.raises(ValidationError):
        Segment(source_id="s", start_offset=start, end_offset=end, text="x")
    with pytest.raises(ValidationError):
        Evidence(
            evidence_key="k",
            target_type=TargetType.claim,
            target_id="t",
            source_id="s",
            start_offset=start,
            end_offset=end,
            quote="x",
        )


# ── confidence ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("value", [0.0, 0.5, 1.0])
def test_valid_confidence(value: float):
    assert _claim(confidence=value).confidence == value
    assert Alias(entity_id="e", name="K.", source="ner", confidence=value).confidence == value


@pytest.mark.parametrize("value", [-0.1, 1.1, 2.0])
def test_invalid_confidence_rejected(value: float):
    with pytest.raises(ValidationError):
        _claim(confidence=value)
    with pytest.raises(ValidationError):
        Alias(entity_id="e", name="K.", source="ner", confidence=value)
    with pytest.raises(ValidationError):
        Participation(
            participation_key="k",
            event_id="ev",
            entity_id="e",
            role=Role.autor,
            confidence=value,
            pass_id="p",
        )


# ── Pass.level ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("level", [0, 3, 5])
def test_valid_pass_level(level: int):
    p = Pass(
        level=level, target="doc", calls=0, proposed=0, verified=0,
        stop_reason=PassStopReason.completed,
    )
    assert p.level == level


@pytest.mark.parametrize("level", [-1, 6, 99])
def test_invalid_pass_level_rejected(level: int):
    with pytest.raises(ValidationError):
        Pass(
            level=level, target="doc", calls=0, proposed=0, verified=0,
            stop_reason=PassStopReason.completed,
        )


# ── serialização camelCase ────────────────────────────────────────────────────


def test_json_uses_camel_case_aliases():
    e = Entity(project_id="p1", preferred_name="Josef K.", kind=EntityKind.pessoa)
    dumped = e.model_dump(by_alias=True)
    assert "projectId" in dumped and "preferredName" in dumped
    assert "project_id" not in dumped


def test_populate_by_name_accepts_both():
    by_snake = Entity(project_id="p", preferred_name="K.", kind=EntityKind.pessoa)
    by_camel = Entity.model_validate(
        {"projectId": "p", "preferredName": "K.", "kind": "pessoa"}
    )
    assert by_snake.preferred_name == by_camel.preferred_name


def test_claim_class_serializes_as_class():
    dumped = _claim().model_dump(by_alias=True)
    assert dumped["class"] == ClaimClass.afirmada
    parsed = Claim.model_validate(
        dict(
            claimKey="k", subjectId="s", typeId="t", objectId="o",
            **{"class": "afirmada"}, confidence=0.5, passId="p",
        )
    )
    assert parsed.claim_class is ClaimClass.afirmada

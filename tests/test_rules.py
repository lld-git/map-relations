"""Regras de domínio: kinds compatíveis, transição com ChangeLog, evento com participações."""

import pytest

from map_relations.core.ids import claim_key, participation_key
from map_relations.core.models import (
    Actor,
    ChangeAction,
    Claim,
    ClaimClass,
    ClaimState,
    Entity,
    EntityKind,
    NarrativeScope,
    Participation,
    RelationType,
    Role,
    TargetType,
)
from map_relations.core.ontology import Status
from map_relations.core.rules import (
    AbstractType,
    IncompatibleKinds,
    ObsoleteType,
    ReflexiveClaim,
    new_claim,
    transition,
    validate_claim_kinds,
)
from map_relations.core.states import InvalidTransition


def _entity(kind: EntityKind, name: str = "X") -> Entity:
    return Entity(project_id="p1", preferred_name=name, kind=kind)


ACUSA = RelationType(
    label="acusa",
    definition="sujeito acusa objeto formalmente",
    subject_kinds=[EntityKind.pessoa, EntityKind.grupo],
    object_kinds=[EntityKind.pessoa],
    version=1,
)


def _claim(subject: Entity, object_: Entity, state: ClaimState = ClaimState.proposta) -> Claim:
    return Claim(
        claim_key=claim_key(subject.id, ACUSA, object_.id),
        subject_id=subject.id,
        type_id=ACUSA.id,
        object_id=object_.id,
        claim_class=ClaimClass.afirmada,
        state=state,
        confidence=0.8,
        pass_id="pass1",
    )


# ── validate_claim_kinds ──────────────────────────────────────────────────────


def test_compatible_kinds_pass():
    validate_claim_kinds(ACUSA, _entity(EntityKind.pessoa), _entity(EntityKind.pessoa))
    validate_claim_kinds(ACUSA, _entity(EntityKind.grupo), _entity(EntityKind.pessoa))


def test_incompatible_subject_kind_rejected():
    with pytest.raises(IncompatibleKinds, match="sujeito"):
        validate_claim_kinds(ACUSA, _entity(EntityKind.lugar), _entity(EntityKind.pessoa))


def test_incompatible_object_kind_rejected():
    with pytest.raises(IncompatibleKinds, match="objeto"):
        validate_claim_kinds(ACUSA, _entity(EntityKind.pessoa), _entity(EntityKind.objeto))


# ── transition com ChangeLog ──────────────────────────────────────────────────


def test_transition_returns_new_instance_and_changelog():
    josef = _entity(EntityKind.pessoa, "Josef K.")
    tribunal = _entity(EntityKind.pessoa, "Juiz")
    claim = _claim(tribunal, josef)

    updated, log = transition(claim, ClaimState.verificada, Actor.auto, pass_id="pass1")

    assert claim.state is ClaimState.proposta  # original intocado
    assert updated.state is ClaimState.verificada
    assert updated.id == claim.id
    assert log.action is ChangeAction.state_change
    assert log.actor is Actor.auto
    assert log.target_type is TargetType.claim
    assert log.target_id == claim.id
    assert log.before == {"state": "proposta"}
    assert log.after == {"state": "verificada"}
    assert log.pass_id == "pass1"


def test_transition_rejects_auto_on_human_state():
    claim = _claim(
        _entity(EntityKind.pessoa), _entity(EntityKind.pessoa),
        state=ClaimState.confirmada_humano,
    )
    with pytest.raises(InvalidTransition):
        transition(claim, ClaimState.rejeitada, Actor.auto)


def test_transition_participation_logs_participation_target():
    part = Participation(
        participation_key=participation_key("ev1", "ent1", Role.testemunha.value),
        event_id="ev1",
        entity_id="ent1",
        role=Role.testemunha,
        confidence=0.7,
        pass_id="pass1",
    )
    updated, log = transition(part, ClaimState.confirmada_humano, Actor.humano)
    assert updated.state is ClaimState.confirmada_humano
    assert log.target_type is TargetType.participation
    assert log.actor is Actor.humano


# ── evento com participações ──────────────────────────────────────────────────


def test_event_with_participations():
    """Critério do B01: criar um evento (entity kind=evento) com participações."""
    prisao = _entity(EntityKind.evento, "Prisão de Josef K.")
    josef = _entity(EntityKind.pessoa, "Josef K.")
    guardas = _entity(EntityKind.grupo, "Guardas")

    parts = [
        Participation(
            participation_key=participation_key(prisao.id, josef.id, Role.alvo.value),
            event_id=prisao.id,
            entity_id=josef.id,
            role=Role.alvo,
            confidence=0.9,
            pass_id="pass1",
        ),
        Participation(
            participation_key=participation_key(prisao.id, guardas.id, Role.autor.value),
            event_id=prisao.id,
            entity_id=guardas.id,
            role=Role.autor,
            confidence=0.9,
            pass_id="pass1",
        ),
    ]

    assert prisao.kind is EntityKind.evento
    assert all(p.event_id == prisao.id for p in parts)
    assert all(p.state is ClaimState.proposta for p in parts)
    assert len({p.participation_key for p in parts}) == 2


def test_participation_key_upsert_identity():
    """Mesma (evento, entidade, papel) → mesma chave, independente do UUID."""
    a = participation_key("ev", "ent", Role.autor.value)
    b = participation_key("ev", "ent", Role.autor.value)
    assert a == b


# ── new_claim ─────────────────────────────────────────────────────────────────


def _onto(**type_extra):
    from map_relations.core.ontology import build_ontology

    t = {
        "id": "acusa", "version": 1, "status": "active", "replaced_by": [],
        "label": "Acusa", "definition": "d", "when_to_use": "u", "when_not_to_use": "n",
        "example": "e", "parent": "fam", "domain": ["pessoa", "grupo"], "range": ["pessoa"],
        "symmetric": False, "inverse_of": {"id": "acusado_por", "label": "Acusado por"},
        "irreflexive": True, "disjoint_with": [], "disjoint_note": None,
    }
    t.update(type_extra)
    return build_ontology({
        "version": 1,
        "abstract_types": [{
            "id": "fam", "label": "F", "definition": "d",
            "domain": ["pessoa", "grupo"], "range": ["pessoa"], "status": "active",
        }],
        "types": [t],
    })


def _rt(onto):
    return onto.relation_types()[0]


def _args(onto, s=None, o=None):
    return (
        onto, _rt(onto),
        s or _entity(EntityKind.pessoa, "A"), o or _entity(EntityKind.pessoa, "B"),
    )


def test_new_claim_builds_claim_with_key():
    onto = _onto()
    a, b = _entity(EntityKind.pessoa, "A"), _entity(EntityKind.pessoa, "B")
    c = new_claim(
        onto, _rt(onto), a, b, claim_class=ClaimClass.afirmada, confidence=0.9, pass_id="p"
    )
    assert c.claim_key == claim_key(a.id, _rt(onto), b.id)
    assert (c.subject_id, c.type_id, c.object_id) == (a.id, "acusa", b.id)


def test_new_claim_alegada_puts_asserted_by_in_key():
    onto = _onto()
    a, b = _entity(EntityKind.pessoa, "A"), _entity(EntityKind.pessoa, "B")
    kw = dict(confidence=0.9, pass_id="p")
    plain = new_claim(onto, _rt(onto), a, b, claim_class=ClaimClass.afirmada, **kw)
    alleged = new_claim(
        onto, _rt(onto), a, b, claim_class=ClaimClass.alegada, asserted_by=a.id,
        narrative_scope=NarrativeScope.texto_encaixado, **kw,
    )
    assert alleged.claim_key != plain.claim_key
    assert alleged.asserted_by == a.id


def test_new_claim_rejects_abstract_type():
    onto = _onto()
    abstract = RelationType(
        id="fam", label="F", definition="d", subject_kinds=[EntityKind.pessoa],
        object_kinds=[EntityKind.pessoa], version=1,
    )
    with pytest.raises(AbstractType):
        new_claim(
            onto, abstract, _entity(EntityKind.pessoa), _entity(EntityKind.pessoa),
            claim_class=ClaimClass.afirmada, confidence=0.9, pass_id="p",
        )


def test_new_claim_rejects_obsolete_type():
    onto = _onto()
    onto.file.types[0].status = Status.obsolete
    with pytest.raises(ObsoleteType):
        new_claim(
            *_args(onto), claim_class=ClaimClass.afirmada, confidence=0.9, pass_id="p"
        )


def test_new_claim_rejects_reflexive_claim():
    onto = _onto()
    a = _entity(EntityKind.pessoa, "A")
    with pytest.raises(ReflexiveClaim):
        new_claim(
            *_args(onto, a, a), claim_class=ClaimClass.afirmada, confidence=0.9, pass_id="p"
        )


def test_new_claim_accepts_reflexive_when_type_is_not_irreflexive():
    onto = _onto(irreflexive=False)
    a = _entity(EntityKind.pessoa, "A")
    c = new_claim(*_args(onto, a, a), claim_class=ClaimClass.afirmada, confidence=0.9, pass_id="p")
    assert c.subject_id == c.object_id


def test_new_claim_rejects_incompatible_kind():
    onto = _onto()
    with pytest.raises(IncompatibleKinds):
        new_claim(
            *_args(onto, _entity(EntityKind.lugar)),
            claim_class=ClaimClass.afirmada, confidence=0.9, pass_id="p",
        )

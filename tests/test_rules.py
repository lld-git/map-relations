"""Regras de domínio: kinds compatíveis, transição com ChangeLog, evento com participações."""

import pytest

from research.map_relations.core.ids import claim_key, participation_key
from research.map_relations.core.models import (
    Actor,
    ChangeAction,
    Claim,
    ClaimClass,
    ClaimState,
    Entity,
    EntityKind,
    Participation,
    RelationType,
    Role,
    TargetType,
)
from research.map_relations.core.rules import (
    IncompatibleKinds,
    transition,
    validate_claim_kinds,
)
from research.map_relations.core.states import InvalidTransition


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
        claim_key=claim_key(subject.id, ACUSA.id, object_.id),
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

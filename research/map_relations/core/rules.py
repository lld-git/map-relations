"""Regras de domínio que cruzam mais de um modelo."""

from research.map_relations.core.models import (
    Actor,
    ChangeAction,
    ChangeLog,
    Claim,
    ClaimState,
    Entity,
    Participation,
    RelationType,
    TargetType,
)
from research.map_relations.core.states import validate_transition


class IncompatibleKinds(ValueError):
    pass


def validate_claim_kinds(
    relation_type: RelationType, subject: Entity, object_: Entity
) -> None:
    """Rejeita claims cujo sujeito ou objeto não têm kind aceito pelo relationType."""
    if subject.kind not in relation_type.subject_kinds:
        raise IncompatibleKinds(
            f"sujeito kind={subject.kind.value} não aceito por "
            f"{relation_type.label} (aceita: "
            f"{[k.value for k in relation_type.subject_kinds]})"
        )
    if object_.kind not in relation_type.object_kinds:
        raise IncompatibleKinds(
            f"objeto kind={object_.kind.value} não aceito por "
            f"{relation_type.label} (aceita: "
            f"{[k.value for k in relation_type.object_kinds]})"
        )


def transition(
    item: Claim | Participation,
    new_state: ClaimState,
    actor: Actor,
    *,
    run_id: str | None = None,
    pass_id: str | None = None,
) -> tuple[Claim | Participation, ChangeLog]:
    """Aplica uma transição de estado validada e registra no ChangeLog.

    Retorna uma nova instância (os modelos são imutáveis por convenção)
    e a entrada de ChangeLog correspondente. Lança InvalidTransition
    se a mudança violar o ADR 006.
    """
    validate_transition(item.state, new_state, actor)
    updated = item.model_copy(update={"state": new_state})
    target_type = (
        TargetType.claim if isinstance(item, Claim) else TargetType.participation
    )
    log = ChangeLog(
        action=ChangeAction.state_change,
        actor=actor,
        target_type=target_type,
        target_id=item.id,
        before={"state": item.state.value},
        after={"state": new_state.value},
        run_id=run_id,
        pass_id=pass_id,
    )
    return updated, log

"""Regras de domínio que cruzam mais de um modelo."""

from map_relations.core.ids import claim_key
from map_relations.core.models import (
    Actor,
    ChangeAction,
    ChangeLog,
    Claim,
    ClaimClass,
    ClaimState,
    Entity,
    NarrativeScope,
    Participation,
    RelationType,
    TargetType,
)
from map_relations.core.ontology import AbstractTypeDef, Ontology, Status
from map_relations.core.states import validate_transition


class IncompatibleKinds(ValueError):
    pass


class AbstractType(ValueError):
    """Tipo abstrato não é anotável."""


class ObsoleteType(ValueError):
    """Tipo obsoleto não recebe claims novas."""


class ReflexiveClaim(ValueError):
    """Sujeito e objeto são a mesma entidade em tipo irreflexivo."""


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


def new_claim(
    ontology: Ontology,
    relation_type: RelationType,
    subject: Entity,
    object_: Entity,
    *,
    claim_class: ClaimClass,
    confidence: float,
    pass_id: str,
    asserted_by: str | None = None,
    narrative_scope: NarrativeScope | None = None,
) -> Claim:
    """Único caminho de criação de claim no pipeline (ADR 011).

    Rejeita tipo abstrato, tipo obsoleto, claim reflexiva em tipo irreflexivo e
    kind incompatível. Disjunção não é checada aqui: é alerta
    (`Ontology.disjoint_conflicts`), não rejeição.
    """
    definition = ontology.get(relation_type.id)
    if isinstance(definition, AbstractTypeDef):
        raise AbstractType(f"{relation_type.id} é abstrato e não pode ser anotado")
    if definition.status is Status.obsolete:
        raise ObsoleteType(
            f"{relation_type.id} é obsoleto (use: {', '.join(definition.replaced_by)})"
        )
    if definition.irreflexive and subject.id == object_.id:
        raise ReflexiveClaim(f"{relation_type.id} não admite sujeito igual ao objeto")
    validate_claim_kinds(relation_type, subject, object_)
    return Claim(
        claim_key=claim_key(
            subject.id,
            relation_type,
            object_.id,
            asserted_by=asserted_by,
            narrative_scope=narrative_scope.value if narrative_scope else None,
        ),
        subject_id=subject.id,
        type_id=relation_type.id,
        object_id=object_.id,
        claim_class=claim_class,
        confidence=confidence,
        pass_id=pass_id,
        asserted_by=asserted_by,
        narrative_scope=narrative_scope,
    )

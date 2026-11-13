"""Testa todos os pares da tabela de transições do ADR 006 (5×5×2)."""

import pytest

from research.map_relations.core.models import Actor, ClaimState
from research.map_relations.core.states import (
    InvalidTransition,
    can_transition,
    is_terminal,
    validate_transition,
)

AUTO_STATES = {ClaimState.proposta, ClaimState.verificada, ClaimState.rejeitada}
HUMAN_STATES = {ClaimState.confirmada_humano, ClaimState.rejeitada_humano}

STATES: list[ClaimState] = list(ClaimState)
ACTORS: list[Actor] = list(Actor)
ALL_PAIRS: list[tuple[ClaimState, ClaimState, Actor]] = [
    (current, new, actor) for current in STATES for new in STATES for actor in ACTORS
]


def expected(current: ClaimState, new: ClaimState, actor: Actor) -> bool:
    """Reimplementação independente da tabela do ADR 006."""
    if current == new:
        return False
    if actor is Actor.auto:
        return current in AUTO_STATES and new in AUTO_STATES
    return new in HUMAN_STATES


@pytest.mark.parametrize(
    "current,new,actor",
    ALL_PAIRS,
    ids=[f"{c.value}->{n.value}:{a.value}" for c, n, a in ALL_PAIRS],
)
def test_transition_table_complete(current: ClaimState, new: ClaimState, actor: Actor):
    allowed = expected(current, new, actor)
    assert can_transition(current, new, actor) is allowed
    if allowed:
        validate_transition(current, new, actor)  # não lança
    else:
        with pytest.raises(InvalidTransition):
            validate_transition(current, new, actor)


@pytest.mark.parametrize("human_state", sorted(HUMAN_STATES))
@pytest.mark.parametrize("new", list(ClaimState))
def test_auto_never_touches_human_states(human_state: ClaimState, new: ClaimState):
    """Princípio 5: auto nunca altera estado humano, para nenhum destino."""
    assert not can_transition(human_state, new, Actor.auto)


def test_human_can_correct_own_decision():
    validate_transition(
        ClaimState.confirmada_humano, ClaimState.rejeitada_humano, Actor.humano
    )
    validate_transition(
        ClaimState.rejeitada_humano, ClaimState.confirmada_humano, Actor.humano
    )


def test_human_cannot_return_to_auto_states():
    for target in AUTO_STATES:
        assert not can_transition(ClaimState.confirmada_humano, target, Actor.humano)
        assert not can_transition(ClaimState.verificada, target, Actor.humano)


def test_same_state_is_invalid_for_both_actors():
    for state in ClaimState:
        for actor in Actor:
            assert not can_transition(state, state, actor)


def test_is_terminal_only_for_human_states():
    for state in ClaimState:
        assert is_terminal(state) is (state in HUMAN_STATES)


def test_invalid_transition_carries_context():
    with pytest.raises(InvalidTransition) as exc:
        validate_transition(
            ClaimState.confirmada_humano, ClaimState.proposta, Actor.auto
        )
    assert exc.value.current is ClaimState.confirmada_humano
    assert exc.value.new is ClaimState.proposta
    assert exc.value.actor is Actor.auto

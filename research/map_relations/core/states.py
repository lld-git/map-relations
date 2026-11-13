"""Transições de estado de claims e participations — fonte da verdade: ADR 006.

Auto move livremente entre proposta, verificada e rejeitada.
Humano move de qualquer estado para qualquer estado humano, inclusive
corrigindo a si mesmo. Estados humanos nunca são alterados por auto
(Princípio 5 do CLAUDE.md).
"""

from research.map_relations.core.models import Actor, ClaimState

_AUTO_STATES = frozenset(
    {ClaimState.proposta, ClaimState.verificada, ClaimState.rejeitada}
)
_HUMAN_STATES = frozenset(
    {ClaimState.confirmada_humano, ClaimState.rejeitada_humano}
)


class InvalidTransition(ValueError):
    def __init__(self, current: ClaimState, new: ClaimState, actor: Actor) -> None:
        self.current = current
        self.new = new
        self.actor = actor
        super().__init__(
            f"transição inválida: {current.value} → {new.value} por {actor.value}"
        )


def is_terminal(state: ClaimState) -> bool:
    """Estados humanos são terminais para processamento automático."""
    return state in _HUMAN_STATES


def can_transition(current: ClaimState, new: ClaimState, actor: Actor) -> bool:
    if current == new:
        return False
    if actor is Actor.auto:
        return current in _AUTO_STATES and new in _AUTO_STATES
    # humano: pode mover de qualquer estado para qualquer estado humano
    return new in _HUMAN_STATES


def validate_transition(current: ClaimState, new: ClaimState, actor: Actor) -> None:
    """Lança InvalidTransition se a mudança não for permitida (ADR 006)."""
    if not can_transition(current, new, actor):
        raise InvalidTransition(current, new, actor)

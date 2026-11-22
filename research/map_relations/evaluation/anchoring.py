"""Rotina de âncora (B02 §4 e §5, ADR 012).

Dada uma citação (`exact`) e, opcionalmente, o contexto e a posição antigos,
acha a ocorrência certa no canônico atual e devolve a âncora completa.

Regra central: **nunca chute**. A escolha entre ocorrências só usa o `exact` e
o `prefix`/`suffix` gravados. O offset antigo, a distância a ele, um ordinal
ou um casamento aproximado jamais decidem; o offset antigo só volta no
resultado como informação.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from map_relations.evaluation.gold import Anchor

CONTEXT_BASE = 32  # code points de cada lado (D7)
CONTEXT_LIMIT = 128
CONTEXT_STEP = 16


class AnchorInput(BaseModel):
    """Evidência como o anotador a entrega: só `exact` é obrigatório.

    Modo âncora mínima: sem contexto nem posição, a rotina preenche o resto.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    exact: str = Field(min_length=1)
    prefix: str = ""
    suffix: str = ""
    start_offset: int | None = Field(default=None, alias="startOffset")
    end_offset: int | None = Field(default=None, alias="endOffset")


class AnchorErrorKind(enum.StrEnum):
    ambigua = "ambigua"
    nao_encontrada = "nao_encontrada"


@dataclass(frozen=True)
class Occurrence:
    start: int
    end: int


@dataclass(frozen=True)
class AnchorError:
    kind: AnchorErrorKind
    candidates: tuple[Occurrence, ...] = ()
    # quantas candidatas batiam com o contexto gravado (0 = nenhuma resolveu)
    matching_context: int = 0


@dataclass(frozen=True)
class AnchorResolved:
    anchor: Anchor
    old_start: int | None
    old_end: int | None
    filled: bool  # entrada só com `exact`: posição e contexto preenchidos
    moved: bool  # havia posição antiga e ela mudou
    context_updated: bool  # havia contexto gravado e ele mudou (aviso, D3)

    @property
    def unchanged(self) -> bool:
        return not (self.filled or self.moved or self.context_updated)


def find_occurrences(text: str, exact: str) -> list[Occurrence]:
    """Todas as ocorrências de `exact`, inclusive as que se sobrepõem."""
    out: list[Occurrence] = []
    i = text.find(exact)
    while i != -1:
        out.append(Occurrence(i, i + len(exact)))
        i = text.find(exact, i + 1)
    return out


def _context_at(text: str, start: int, end: int, size: int) -> tuple[str, str]:
    """Contexto de até `size` code points de cada lado, sem cortar palavra:
    a borda externa recua para dentro até cair num limite de palavra."""
    ps = max(0, start - size)
    while 0 < ps < start and text[ps - 1].isalnum() and text[ps].isalnum():
        ps += 1
    se = min(len(text), end + size)
    while end < se < len(text) and text[se - 1].isalnum() and text[se].isalnum():
        se -= 1
    return text[ps:start], text[end:se]


def build_context(
    text: str, start: int, end: int, *, base: int = CONTEXT_BASE, limit: int = CONTEXT_LIMIT
) -> tuple[str, str] | None:
    """Menor contexto (a partir de `base`, crescendo até `limit`) que deixa
    prefix + exact + suffix único no texto; None se nem `limit` basta."""
    size = base
    while True:
        prefix, suffix = _context_at(text, start, end, size)
        if len(find_occurrences(text, prefix + text[start:end] + suffix)) == 1:
            return prefix, suffix
        if size >= limit:
            return None
        size = min(size + CONTEXT_STEP, limit)


def _context_matches(text: str, occ: Occurrence, prefix: str, suffix: str) -> bool:
    """O contexto gravado está colado na ocorrência? Vazio casa com qualquer coisa."""
    if prefix and text[max(0, occ.start - len(prefix)) : occ.start] != prefix:
        return False
    return not suffix or text[occ.end : occ.end + len(suffix)] == suffix


def resolve_anchor(text: str, entry: AnchorInput) -> AnchorResolved | AnchorError:
    """Passos 1 a 5 do §5 para uma evidência."""
    found = find_occurrences(text, entry.exact)
    if not found:
        return AnchorError(AnchorErrorKind.nao_encontrada)
    if len(found) == 1:
        chosen = found[0]
    else:
        fits = [o for o in found if _context_matches(text, o, entry.prefix, entry.suffix)]
        if len(fits) != 1:
            return AnchorError(AnchorErrorKind.ambigua, tuple(found), len(fits))
        chosen = fits[0]
    context = build_context(text, chosen.start, chosen.end)
    if context is None:  # trechos repetidos além de 128 code points de cada lado
        return AnchorError(AnchorErrorKind.ambigua, tuple(found), 1)
    prefix, suffix = context
    anchor = Anchor(
        exact=entry.exact,
        prefix=prefix,
        suffix=suffix,
        start_offset=chosen.start,
        end_offset=chosen.end,
    )
    had_context = bool(entry.prefix or entry.suffix)
    return AnchorResolved(
        anchor=anchor,
        old_start=entry.start_offset,
        old_end=entry.end_offset,
        filled=entry.start_offset is None and not had_context,
        moved=entry.start_offset is not None and entry.start_offset != chosen.start,
        context_updated=had_context and (entry.prefix, entry.suffix) != (prefix, suffix),
    )


def words_around(
    text: str, start: int, end: int, bounds: tuple[int, int], *, words: int = 5
) -> tuple[str, str]:
    """Só as `words` palavras antes e depois da citação, dentro do parágrafo
    (`bounds`). Nunca devolve a citação nem mais do que isso (princípio 6)."""
    lo, hi = bounds
    before = text[lo:start].split()[-words:]
    after = text[end:hi].split()[:words]
    return " ".join(before), " ".join(after)


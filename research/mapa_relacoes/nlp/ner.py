"""
Adaptado de src/nlp/ner.py do projeto Grafo.
Mudanças: adiciona Mention com offsets de caractere; extract_mentions substitui
extract_people. A lógica _merge_partial_names e _contains_whole é preservada intacta.
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spacy.language

_NLP: "spacy.language.Language | None" = None


def _get_nlp() -> "spacy.language.Language":
    global _NLP
    if _NLP is None:
        import spacy

        _NLP = spacy.load("pt_core_news_sm")
    return _NLP


@dataclass(frozen=True)
class Mention:
    """Uma ocorrência nomeada no texto, com posição de caractere."""

    surface: str  # nome como aparece no texto
    start: int    # offset inicial no texto fonte (inclusivo)
    end: int      # offset final no texto fonte (exclusivo)


def _contains_whole(haystack: str, needle: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack) is not None


def _merge_partial_names(names: set[str]) -> list[str]:
    """Funde nomes parciais ('Anderson') no nome mais completo ('Anderson Torres')
    quando há exatamente um candidato mais longo que o contém.
    Casos ambíguos são mantidos separados para não fundir errado.
    """
    by_length_desc = sorted(names, key=len, reverse=True)
    canonical: list[str] = []

    for name in by_length_desc:
        matches = [c for c in canonical if _contains_whole(c, name)]
        if len(matches) != 1:
            canonical.append(name)

    return sorted(canonical)


def extract_mentions(text: str) -> list[Mention]:
    """Extrai entidades PER do texto com offsets de caractere.

    O modelo spaCy é carregado na primeira chamada (lazy). Requer
    pt_core_news_sm instalado: `python -m spacy download pt_core_news_sm`.

    Marcado com requires_spacy_model em testes.
    """
    doc = _get_nlp()(text)

    raw: dict[str, list[Mention]] = {}
    for ent in doc.ents:
        if ent.label_ == "PER":
            surface = ent.text.strip()
            mention = Mention(surface=surface, start=ent.start_char, end=ent.end_char)
            raw.setdefault(surface, []).append(mention)

    canonical_set = set(_merge_partial_names(set(raw.keys())))

    result: list[Mention] = []
    for surface, mentions in raw.items():
        if surface in canonical_set:
            result.extend(mentions)

    return sorted(result, key=lambda m: m.start)


def unique_names(mentions: list[Mention]) -> list[str]:
    """Retorna nomes canônicos únicos e ordenados de uma lista de menções."""
    return sorted({m.surface for m in mentions})

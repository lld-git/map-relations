import pytest

from map_relations.nlp.ner import (
    Mention,
    _contains_whole,
    _merge_partial_names,
    unique_names,
)


def test_merge_partial_names_keeps_full():
    names = {"Anderson Torres", "Anderson", "Torres"}
    result = _merge_partial_names(names)
    assert "Anderson Torres" in result
    assert "Anderson" not in result
    assert "Torres" not in result


def test_merge_partial_names_keeps_ambiguous():
    # "Torres" aparece em "Anderson Torres" e "Carlos Torres" — ambíguo, mantém
    names = {"Anderson Torres", "Carlos Torres", "Torres"}
    result = _merge_partial_names(names)
    assert "Torres" in result


def test_merge_partial_names_single_name():
    names = {"Lula"}
    assert _merge_partial_names(names) == ["Lula"]


def test_merge_partial_names_empty():
    assert _merge_partial_names(set()) == []


def test_contains_whole_matches_word_boundary():
    assert _contains_whole("Anderson Torres", "Anderson") is True
    assert _contains_whole("NandoAnderson", "Anderson") is False
    assert _contains_whole("Carlos Torres Silva", "Torres") is True


def test_unique_names_deduplicates():
    mentions = [
        Mention(surface="Josef K.", start=0, end=8),
        Mention(surface="Josef K.", start=50, end=58),
        Mention(surface="Leni", start=20, end=24),
    ]
    assert unique_names(mentions) == ["Josef K.", "Leni"]


@pytest.mark.requires_spacy_model
def test_extract_mentions_returns_positions():
    from map_relations.nlp.ner import extract_mentions

    text = "Josef K. foi preso pela manhã. O inspetor acompanhou o processo."
    mentions = extract_mentions(text)
    for m in mentions:
        assert text[m.start : m.end].strip() == m.surface

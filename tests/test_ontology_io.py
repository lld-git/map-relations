"""Leitura do YAML da ontologia (borda de I/O)."""

import pytest

from map_relations.core.ontology import OntologyError
from map_relations.ontology_io import load_ontology, parse_yaml


def test_duplicate_yaml_key_rejected():
    with pytest.raises(OntologyError) as e:
        parse_yaml("version: 1\nversion: 2\n")
    assert "chave duplicada 'version'" in str(e.value)
    assert "linha 2" in str(e.value)


def test_duplicate_key_in_nested_mapping_rejected():
    with pytest.raises(OntologyError, match="chave duplicada 'a'"):
        parse_yaml("x:\n  a: 1\n  a: 2\n")


def test_missing_file(tmp_path):
    with pytest.raises(OntologyError):
        load_ontology(tmp_path / "nada.yaml")


def test_root_must_be_mapping(tmp_path):
    p = tmp_path / "o.yaml"
    p.write_text("- 1\n", encoding="utf-8")
    with pytest.raises(OntologyError, match="mapeamento"):
        load_ontology(p)


def test_validation_errors_reach_loader(tmp_path):
    p = tmp_path / "o.yaml"
    p.write_text("version: 1\nabstract_types: []\ntypes: []\nextra: 1\n", encoding="utf-8")
    with pytest.raises(OntologyError, match="extra"):
        load_ontology(p)

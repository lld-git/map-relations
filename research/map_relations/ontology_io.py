"""Borda de I/O da ontologia: lê o YAML rejeitando chave duplicada."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from yaml.constructor import ConstructorError

from map_relations.core.ontology import Ontology, OntologyError, build_ontology

DEFAULT_PATH = Path("contracts/ontology/relations.yaml")


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader que falha em chave duplicada (o PyYAML sobrescreveria em silêncio)."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        self.flatten_mapping(node)
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)  # type: ignore[no-untyped-call]
            if key in seen:
                raise ConstructorError(
                    None,
                    None,
                    f"chave duplicada {key!r} (linha {key_node.start_mark.line + 1})",
                    key_node.start_mark,
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def parse_yaml(text: str) -> Any:
    try:
        return yaml.load(text, Loader=_UniqueKeyLoader)  # noqa: S506 - SafeLoader
    except yaml.YAMLError as exc:
        raise OntologyError([f"yaml: {exc}"]) from exc


def read_yaml(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OntologyError([f"{path}: {exc.strerror or exc}"]) from exc
    return parse_yaml(text)


def load_ontology(path: Path = DEFAULT_PATH) -> Ontology:
    data = read_yaml(path)
    if not isinstance(data, dict):
        raise OntologyError([f"{path}: a raiz deve ser um mapeamento"])
    return build_ontology(data)

"""Gera os artefatos da ontologia a partir de contracts/ontology/relations.yaml.

Uso:
    uv run python -m scripts.generate_ontology           # grava os arquivos
    uv run python -m scripts.generate_ontology --check   # falha se desatualizado (CI)

Artefatos: relation-types.json, ontology.json, relations.lock.json (em
contracts/ontology/) e contracts/schemas/ontology-file.json.
"""

import json
import sys
from pathlib import Path
from typing import Any

from map_relations.core.ontology import OntologyError, OntologyFile
from map_relations.core.ontology_lock import update_lock
from map_relations.ontology_io import load_ontology

ROOT = Path(__file__).parent.parent
ONTOLOGY_DIR = ROOT / "contracts" / "ontology"
YAML_PATH = ONTOLOGY_DIR / "relations.yaml"
LOCK_PATH = ONTOLOGY_DIR / "relations.lock.json"
SCHEMA_PATH = ROOT / "contracts" / "schemas" / "ontology-file.json"


def _dump(obj: Any, *, sort_keys: bool) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=sort_keys) + "\n"


def render_all(lock_path: Path = LOCK_PATH, yaml_path: Path = YAML_PATH) -> dict[Path, str]:
    """Conteúdo esperado de cada artefato; levanta OntologyError se algo violar a trava."""
    onto = load_ontology(yaml_path)
    previous = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else None
    out_dir = yaml_path.parent
    types = [rt.model_dump(mode="json", by_alias=True) for rt in onto.relation_types()]
    return {
        out_dir / "relation-types.json": _dump(types, sort_keys=False),
        out_dir / "ontology.json": _dump(onto.to_dict(), sort_keys=False),
        lock_path: _dump(update_lock(onto, previous), sort_keys=True),
        SCHEMA_PATH: _dump(OntologyFile.model_json_schema(), sort_keys=True),
    }


def main(check: bool) -> int:
    try:
        files = render_all()
    except OntologyError as exc:
        print(f"ontologia inválida:\n{exc}", file=sys.stderr)
        return 1
    if check:
        stale = [p.name for p, c in files.items() if not p.exists() or p.read_text("utf-8") != c]
        if stale:
            print(
                "artefatos da ontologia desatualizados: "
                + ", ".join(stale)
                + "\nrode: uv run python -m scripts.generate_ontology",
                file=sys.stderr,
            )
            return 1
        print(f"{len(files)} artefatos da ontologia em dia")
        return 0
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        print(f"gravado: {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv))

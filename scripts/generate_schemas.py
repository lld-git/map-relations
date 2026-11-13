"""Gera JSON Schema em contracts/schemas a partir dos modelos do core.

Uso:
    uv run python -m scripts.generate_schemas           # grava os arquivos
    uv run python -m scripts.generate_schemas --check   # falha se desatualizado (CI)
"""

import json
import sys
from pathlib import Path

from pydantic import BaseModel

from research.map_relations.core import models

ROOT = Path(__file__).parent.parent
SCHEMAS_DIR = ROOT / "contracts" / "schemas"

DOMAIN_MODELS: list[type[BaseModel]] = [
    models.Source,
    models.Entity,
    models.Alias,
    models.Mention,
    models.RelationType,
    models.Segment,
    models.Claim,
    models.Participation,
    models.Evidence,
    models.TimeScope,
    models.Lens,
    models.Pass,
    models.Run,
    models.ChangeLog,
    models.Note,
]


def _to_kebab(name: str) -> str:
    out = []
    for i, ch in enumerate(name):
        if ch.isupper() and i > 0:
            out.append("-")
        out.append(ch.lower())
    return "".join(out)


def render(model: type[BaseModel]) -> str:
    schema = model.model_json_schema(by_alias=True)
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main(check: bool) -> int:
    SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    stale: list[str] = []
    for model in DOMAIN_MODELS:
        path = SCHEMAS_DIR / f"{_to_kebab(model.__name__)}.json"
        content = render(model)
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(path.name)
        else:
            path.write_text(content, encoding="utf-8")
            print(f"gravado: {path.relative_to(ROOT)}")
    if check and stale:
        print(
            "schemas desatualizados: "
            + ", ".join(stale)
            + "\nrode: uv run python scripts/generate_schemas.py",
            file=sys.stderr,
        )
        return 1
    if check:
        print(f"{len(DOMAIN_MODELS)} schemas em dia")
    return 0


if __name__ == "__main__":
    sys.exit(main(check="--check" in sys.argv))

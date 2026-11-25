"""Canônico sintético e gravação em disco para os testes de fill-offsets e conversão.

O texto é inventado; nenhum trecho de obra protegida entra aqui.
"""

from __future__ import annotations

from pathlib import Path

from map_relations.core.ingest_contract import IngestResult
from map_relations.ingest.markdown import parse_markdown

COMMON = "palavra " * 10  # 80 code points: mais que os 32 do contexto padrão

MD = (
    "# Capítulo I\n\n"
    "Ana vigiava Bruno todos os dias, de manhã e de noite, sem explicar nada a ninguém.\n\n"
    "Carla disse que a chave velha estava na gaveta. Depois Ana guardou a chave velha no bolso.\n\n"
    f"alfa {COMMON}CITA{COMMON}beta\n\n"
    "# Capítulo II\n\n"
    f"gama {COMMON}CITA{COMMON}delta\n\n"
    "Bruno respondeu que a chave velha sumiu de novo.\n"
)


def make_canon() -> IngestResult:
    return parse_markdown(MD, title="sintetico", kind="txt")


def write_processed(root: Path, canon: IngestResult) -> Path:
    """Grava canonical.txt + ingest.json como o `ingest` faz; devolve o canonical.txt."""
    d = root / "processed" / canon.source.content_hash[:8]
    d.mkdir(parents=True)
    (d / "canonical.txt").write_bytes(canon.text.encode("utf-8"))
    (d / "ingest.json").write_text(
        canon.model_dump_json(by_alias=True, exclude={"text"}), encoding="utf-8"
    )
    return d / "canonical.txt"

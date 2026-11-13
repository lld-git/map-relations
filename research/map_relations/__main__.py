"""CLI do map_relations.

Uso (no contêiner, com PYTHONPATH=/app/research já definido na imagem):
    python -m map_relations ingest <pdf>

O PDF deve estar em data/raw/. A saída vai para data/processed/<hash>/.
"""

import argparse
import sys
from pathlib import Path

from research.map_relations.ingest.pdf_loader import load_pdf
from research.map_relations.ingest.report import write_processed

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


def cmd_ingest(pdf: str) -> int:
    path = Path(pdf)
    if not path.is_absolute():
        path = RAW_DIR / path
    path = path.resolve()

    if RAW_DIR.resolve() not in path.parents:
        print(f"erro: o PDF deve estar em data/raw/ (recebido: {path})", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"erro: arquivo não encontrado: {path}", file=sys.stderr)
        return 2

    try:
        result = load_pdf(path)
        out_dir = write_processed(result, PROCESSED_DIR)
    except Exception as exc:  # noqa: BLE001 — CLI converte qualquer falha em exit code
        print(f"erro ao processar {path.name}: {exc}", file=sys.stderr)
        return 1

    q = result.quality
    print(f"hash: {result.source.content_hash}")
    print(f"saída: {out_dir}")
    print(
        f"qualidade: {q.pages} páginas, {q.paragraphs} parágrafos, "
        f"{q.chapters_detected} capítulos, "
        f"{sum(q.removed_by_reason.values())} itens removidos, "
        f"{len(q.alerts)} alertas"
    )
    for alert in q.alerts:
        print(f"  alerta: {alert}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="map_relations",
        description="Ferramentas de pesquisa do Mapa de Relações.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_ingest = sub.add_parser(
        "ingest", help="converte um PDF de data/raw/ em data/processed/<hash>/"
    )
    p_ingest.add_argument("pdf", help="arquivo PDF em data/raw/ (nome ou caminho)")
    args = parser.parse_args(argv)

    if args.command == "ingest":
        return cmd_ingest(args.pdf)
    parser.error(f"comando desconhecido: {args.command}")


if __name__ == "__main__":
    sys.exit(main())

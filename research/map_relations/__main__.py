"""CLI do map_relations.

Uso (no contêiner):
    python -m map_relations ingest <pdf>

O PDF deve estar em data/raw/. A saída vai para data/processed/<hash>/.
data/ é resolvido a partir do diretório de trabalho (/app no contêiner),
não do pacote — na imagem prod o pacote vive em site-packages (ADR 007).
"""

import argparse
import sys
from pathlib import Path

from map_relations.ingest.docling_compare import compare, load_docling_json
from map_relations.ingest.pdf_loader import load_pdf
from map_relations.ingest.report import write_processed

ROOT = Path.cwd()
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
DOCLING_DIR = ROOT / "data" / "docling"


def _resolve_raw(pdf: str) -> Path | None:
    path = Path(pdf)
    if not path.is_absolute():
        path = RAW_DIR / path
    path = path.resolve()
    if RAW_DIR.resolve() not in path.parents:
        print(f"erro: o PDF deve estar em data/raw/ (recebido: {path})", file=sys.stderr)
        return None
    if not path.is_file():
        print(f"erro: arquivo não encontrado: {path}", file=sys.stderr)
        return None
    return path


def cmd_compare(pdf: str) -> int:
    path = _resolve_raw(pdf)
    if path is None:
        return 2
    docling_json = DOCLING_DIR / f"{path.stem}.json"
    if not docling_json.is_file():
        print(
            f"erro: saída do Docling não encontrada: {docling_json}\n"
            f"rode antes: make docling PDF={path.name}",
            file=sys.stderr,
        )
        return 2
    try:
        result = load_pdf(path)
        report = compare(result, load_docling_json(docling_json))
        out_dir = PROCESSED_DIR / result.source.content_hash
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / "comparacao_docling.md"
        out.write_text(report, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 — CLI converte qualquer falha em exit code
        print(f"erro ao comparar {path.name}: {exc}", file=sys.stderr)
        return 1
    print(f"comparação: {out}")
    return 0


def cmd_ingest(pdf: str) -> int:
    path = _resolve_raw(pdf)
    if path is None:
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
    p_compare = sub.add_parser(
        "compare",
        help="compara pdf_loader e Docling sobre um PDF (requer make docling antes)",
    )
    p_compare.add_argument("pdf", help="arquivo PDF em data/raw/ (nome ou caminho)")
    args = parser.parse_args(argv)

    if args.command == "ingest":
        return cmd_ingest(args.pdf)
    if args.command == "compare":
        return cmd_compare(args.pdf)
    parser.error(f"comando desconhecido: {args.command}")


if __name__ == "__main__":
    sys.exit(main())

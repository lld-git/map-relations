"""CLI do map_relations (fluxo do ADR 008).

    python -m map_relations ingest <arquivo>    # PDF, TXT, EPUB, DOCX, HTML
    python -m map_relations prepare <arquivo>   # imprime o dir de cache Docling
    python -m map_relations compare <pdf> [--converter docling|pdf_loader]
    python -m map_relations clean [--apply]     # pastas órfãs em processed/
    python -m map_relations ontology check [arquivo]  # valida a ontologia de relações
    python -m map_relations gold fill-offsets|convert-draft|validate  # gabarito (B02)

O arquivo deve estar em data/raw/. Saída em data/processed/<hash_do_arquivo>/.
documento.md é a fonte revisada pelo humano: nunca é sobrescrito sem --force-md.
data/ é resolvido a partir do diretório de trabalho (/app no contêiner).

Códigos de saída: 0 ok; 1 falha de processamento; 2 entrada inválida;
3 cache do Docling ausente (o Makefile roda o serviço e tenta de novo).
"""

import argparse
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from map_relations.core.ingest_contract import IngestResult, RemovedItem
from map_relations.evaluation import gold_cli
from map_relations.ingest.alerts import ConversionAlert, classify_conversion_alerts
from map_relations.ingest.canonical import build_ingest_result, pdf_pages_to_blocks
from map_relations.ingest.canonical import layout_items as pdf_loader_layout_items
from map_relations.ingest.convert_docling import merge_range_docs, merged_layout_items
from map_relations.ingest.convert_pandoc import convert_pandoc
from map_relations.ingest.convert_txt import txt_to_blocks
from map_relations.ingest.docling_compare import compare, load_docling_json
from map_relations.ingest.layout import LayoutItem
from map_relations.ingest.markdown import md_hash, parse_markdown, render_markdown
from map_relations.ingest.pdf_loader import extract_pages, page_count, page_ranges
from map_relations.ingest.report import render_report
from map_relations.ingest.store import ProcessedStore, file_hash
from map_relations.ontology_io import DEFAULT_PATH as ONTOLOGY_PATH
from map_relations.ontology_io import load_ontology

ROOT = Path.cwd()
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

_PANDOC_KINDS = {".epub": "epub", ".docx": "docx", ".html": "html", ".htm": "html"}


def _docling_converter(path: Path, store: ProcessedStore, source_hash: str) -> list[LayoutItem]:
    range_files = store.docling_range_files(source_hash)
    if not range_files:
        raise FileNotFoundError(
            f"cache do Docling ausente em {store.docling_cache_dir(source_hash)}\n"
            f"rode antes: make docling PDF={path.name}"
        )
    docs = [load_docling_json(f) for f in range_files]
    items, _removed, _alerts, _pages = merged_layout_items(docs)
    return items


def _pdf_loader_converter(
    path: Path, _store: ProcessedStore, _source_hash: str
) -> list[LayoutItem]:
    return pdf_loader_layout_items(extract_pages(path))


# Conversores registrados para `make compare` (B04d fase 6): qualquer um
# aqui pode ser comparado contra o pdf_loader, sobre a mesma representação
# comum (LayoutItem) — não só Docling. MinerU (B04d B.3) não entra: este
# bloco não escreve adaptador.
CONVERTERS: dict[str, Callable[[Path, ProcessedStore, str], list[LayoutItem]]] = {
    "docling": _docling_converter,
    "pdf_loader": _pdf_loader_converter,
}


def _resolve_raw(name: str) -> Path | None:
    path = Path(name)
    if not path.is_absolute():
        path = RAW_DIR / path
    path = path.resolve()
    if RAW_DIR.resolve() not in path.parents:
        print(f"erro: o arquivo deve estar em data/raw/ (recebido: {path})", file=sys.stderr)
        return None
    if not path.is_file():
        print(f"erro: arquivo não encontrado: {path}", file=sys.stderr)
        return None
    return path


def _kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".txt":
        return "txt"
    return _PANDOC_KINDS.get(suffix, "")


def _generate_md(store: ProcessedStore, path: Path, source_hash: str, kind: str, route: str) -> int:
    """Gera documento.md + conversao.json pela rota adequada. Retorna exit code."""
    out_dir = store.dir_for(source_hash)
    if kind == "pdf" and route == "docling":
        range_files = store.docling_range_files(source_hash)
        if not range_files:
            print(
                f"cache do Docling ausente em {store.docling_cache_dir(source_hash)}\n"
                f"rode: make docling PDF={path.name} (ou use --route pdf_loader)",
                file=sys.stderr,
            )
            return 3
        docs = [load_docling_json(f) for f in range_files]
        blocks, removed, alerts, covered = merge_range_docs(docs)
        total = page_count(path)
        if covered != total:
            print(
                f"cache incompleto: {covered} de {total} páginas convertidas\n"
                f"rode: make docling PDF={path.name}",
                file=sys.stderr,
            )
            return 3
    elif kind == "pdf":  # route == "pdf_loader"
        raw_pages = extract_pages(path)
        raw_dir = out_dir / "pdf_loader"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "raw.json").write_text(
            json.dumps({"pages": raw_pages}, ensure_ascii=False), encoding="utf-8"
        )
        blocks, removed, alerts = pdf_pages_to_blocks(raw_pages)
    elif kind == "txt":
        blocks, removed, alerts = txt_to_blocks(path.read_text(encoding="utf-8"))
    else:  # pandoc
        blocks, removed, alerts = convert_pandoc(path)

    md = render_markdown(blocks)
    store.documento_md(source_hash).write_text(md, encoding="utf-8")
    (out_dir / "conversao.json").write_text(
        json.dumps(
            {
                "rota": route if kind == "pdf" else kind,
                "md_sha256": md_hash(md),  # hash do .md gerado — detecta edição
                "alertas": alerts,
                "removidos": [r.model_dump(by_alias=True) for r in removed],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


def _parse_existing(
    store: ProcessedStore, source_hash: str, title: str, kind: str
) -> tuple[IngestResult, list[ConversionAlert], bool]:
    """Parseia o documento.md atual. Alertas do parser saem em quality.alerts
    (sempre sobre o .md atual); os da conversão vêm classificados à parte."""
    md = store.documento_md(source_hash).read_text(encoding="utf-8")
    removed: list[RemovedItem] = []
    conv_alerts: list[str] = []
    generated_hash = ""
    conv = store.dir_for(source_hash) / "conversao.json"
    if conv.is_file():
        data = json.loads(conv.read_text(encoding="utf-8"))
        conv_alerts = list(data.get("alertas", []))
        generated_hash = data.get("md_sha256", "")
        removed = [RemovedItem.model_validate(r) for r in data.get("removidos", [])]
    edited = bool(generated_hash) and md_hash(md) != generated_hash
    result = parse_markdown(md, title, kind, removed=removed)
    classified = classify_conversion_alerts(conv_alerts, md, edited)
    return result, classified, edited


def cmd_ingest(name: str, route: str, force_md: bool) -> int:
    path = _resolve_raw(name)
    if path is None:
        return 2
    kind = _kind(path)
    if not kind:
        print(f"erro: formato não suportado: {path.suffix}", file=sys.stderr)
        return 2

    try:
        source_hash = file_hash(path)
        store = ProcessedStore(PROCESSED_DIR)
        store.write_source_json(source_hash, file_name=path.name, kind=kind)

        md_path = store.documento_md(source_hash)
        if force_md or not md_path.is_file():
            if md_path.is_file():
                print("aviso: --force-md descarta a revisão humana em documento.md")
            code = _generate_md(store, path, source_hash, kind, route)
            if code != 0:
                return code

        result, conv_alerts, edited = _parse_existing(store, source_hash, path.stem, kind)
        out_dir = store.dir_for(source_hash)
        (out_dir / "canonical.txt").write_text(result.text, encoding="utf-8")
        (out_dir / "ingest.json").write_text(
            result.model_dump_json(by_alias=True, exclude={"text"}, indent=2),
            encoding="utf-8",
        )
        (out_dir / "report.md").write_text(
            render_report(result, conversion_alerts=conv_alerts, edited=edited),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 — CLI converte qualquer falha em exit code
        print(f"erro ao processar {path.name}: {exc}", file=sys.stderr)
        return 1

    q = result.quality
    print(f"hash do arquivo: {source_hash}")
    print(f"hash canônico:   {result.source.content_hash}")
    print(f"saída: {out_dir}")
    print(
        f"qualidade: {q.pages} páginas, {q.paragraphs} parágrafos, "
        f"{q.chapters_detected} capítulos, "
        f"{sum(q.removed_by_reason.values())} itens removidos, "
        f"{len(q.alerts)} alertas"
    )
    for alert in q.alerts:
        print(f"  alerta: {alert}")
    if conv_alerts:
        ativos = sum(not c.resolved for c in conv_alerts)
        resolvidos = len(conv_alerts) - ativos
        estado = "editado" if edited else "não revisado"
        print(
            f"conversão ({estado}): {ativos} alertas ativos, {resolvidos} resolvidos"
        )
    return 0


def cmd_prepare(name: str) -> int:
    """Imprime (só) o diretório relativo do cache Docling — usado pelo Makefile."""
    path = _resolve_raw(name)
    if path is None:
        return 2
    source_hash = file_hash(path)
    store = ProcessedStore(PROCESSED_DIR)
    store.write_source_json(source_hash, file_name=path.name, kind=_kind(path) or "?")
    print(store.docling_cache_dir(source_hash).relative_to(ROOT))
    return 0


def cmd_docling_ranges(name: str, size: int) -> int:
    """Imprime as faixas de página a converter (ex.: '1-40 41-80') — usado pelo
    Makefile para fatiar a conversão do Docling em processos separados."""
    path = _resolve_raw(name)
    if path is None:
        return 2
    ranges = page_ranges(page_count(path), size)
    print(" ".join(f"{s}-{e}" for s, e in ranges))
    return 0


def cmd_compare(name: str, converter: str) -> int:
    path = _resolve_raw(name)
    if path is None:
        return 2
    convert = CONVERTERS.get(converter)
    if convert is None:
        print(
            f"conversor desconhecido: {converter} (registrados: {', '.join(CONVERTERS)})",
            file=sys.stderr,
        )
        return 2
    source_hash = file_hash(path)
    store = ProcessedStore(PROCESSED_DIR)
    try:
        result = build_ingest_result(extract_pages(path), title=path.stem, kind="pdf")
        items = convert(path, store, source_hash)
        report = compare(result, items, converter=converter)
        out = store.dir_for(source_hash) / f"comparacao_{converter}.md"
        out.write_text(report, encoding="utf-8")
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except Exception as exc:  # noqa: BLE001
        print(f"erro ao comparar {path.name}: {exc}", file=sys.stderr)
        return 1
    print(f"comparação: {out}")
    return 0


def cmd_clean(apply: bool) -> int:
    store = ProcessedStore(PROCESSED_DIR)
    orphans = store.orphans(RAW_DIR)
    if not orphans:
        print("nenhuma pasta órfã em data/processed/")
        return 0
    for orphan in orphans:
        if apply:
            shutil.rmtree(orphan)
            print(f"removido: {orphan}")
        else:
            print(f"órfã: {orphan}")
    if not apply:
        print(f"{len(orphans)} pastas órfãs — rode com --apply para remover")
    return 0


def cmd_ontology_check(path: Path) -> int:
    from map_relations.core.ontology import OntologyError

    try:
        onto = load_ontology(path)
    except OntologyError as exc:
        print(f"ontologia inválida ({len(exc.errors)} erro(s)):", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1
    print(
        f"ontologia ok: versão {onto.version}, "
        f"{onto.n_annotatable} anotáveis, {onto.n_abstract} abstratos"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="map_relations",
        description="Ferramentas de pesquisa do Mapa de Relações.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser(
        "ingest", help="converte um arquivo de data/raw/ em data/processed/<hash>/"
    )
    p_ingest.add_argument("arquivo", help="arquivo em data/raw/ (nome ou caminho)")
    p_ingest.add_argument(
        "--route",
        choices=["docling", "pdf_loader"],
        default="docling",
        help="rota de conversão para PDF (padrão: docling, exige cache)",
    )
    p_ingest.add_argument(
        "--force-md",
        action="store_true",
        help="regenera documento.md descartando a revisão humana",
    )

    p_prepare = sub.add_parser(
        "prepare", help="imprime o diretório do cache Docling (uso do Makefile)"
    )
    p_prepare.add_argument("arquivo")

    p_ranges = sub.add_parser(
        "docling-ranges", help="imprime as faixas de página a converter (uso do Makefile)"
    )
    p_ranges.add_argument("arquivo")
    p_ranges.add_argument("--size", type=int, default=40, help="páginas por faixa")

    p_compare = sub.add_parser(
        "compare", help="compara pdf_loader × conversor registrado (requer cache do conversor)"
    )
    p_compare.add_argument("arquivo")
    p_compare.add_argument(
        "--converter",
        choices=sorted(CONVERTERS),
        default="docling",
        help="conversor a comparar contra o pdf_loader (padrão: docling)",
    )

    p_clean = sub.add_parser("clean", help="lista/remove pastas órfãs de processed/")
    p_clean.add_argument("--apply", action="store_true", help="remove de verdade")

    p_onto = sub.add_parser("ontology", help="ferramentas da ontologia de relações")
    onto_sub = p_onto.add_subparsers(dest="onto_command", required=True)
    p_check = onto_sub.add_parser("check", help="valida relations.yaml (exit 1 com a lista)")
    p_check.add_argument("arquivo", nargs="?", type=Path, default=ONTOLOGY_PATH)

    p_gold = sub.add_parser("gold", help="ferramentas do gabarito (B02)")
    gold_sub = p_gold.add_subparsers(dest="gold_command", required=True)
    canon_help = "canonical.txt (padrão: o único em data/processed/)"
    p_fill = gold_sub.add_parser(
        "fill-offsets", help="refaz as âncoras sobre o canônico atual (tudo ou nada)"
    )
    p_fill.add_argument("--gold", type=Path, required=True)
    p_fill.add_argument("--canonical", type=Path, help=canon_help)
    p_fill.add_argument("--out", type=Path, required=True, help="diferente de --gold")
    p_fill.add_argument("--report", type=Path, help="relatório JSON (sem texto da obra)")
    p_conv = gold_sub.add_parser(
        "convert-draft", help="converte o rascunho legado em gabarito (uso único)"
    )
    p_conv.add_argument("--draft", type=Path, required=True)
    p_conv.add_argument("--canonical", type=Path, help=canon_help)
    p_conv.add_argument("--out", type=Path, required=True, help="diferente de --draft")
    p_conv.add_argument("--report", type=Path, help="relatório JSON (sem texto da obra)")
    p_val = gold_sub.add_parser("validate", help="valida o gabarito contra ontologia e canônico")
    p_val.add_argument("--gold", type=Path, required=True)
    p_val.add_argument("--canonical", type=Path, help=canon_help)

    args = parser.parse_args(argv)
    if args.command == "ingest":
        return cmd_ingest(args.arquivo, args.route, args.force_md)
    if args.command == "prepare":
        return cmd_prepare(args.arquivo)
    if args.command == "docling-ranges":
        return cmd_docling_ranges(args.arquivo, args.size)
    if args.command == "compare":
        return cmd_compare(args.arquivo, args.converter)
    if args.command == "clean":
        return cmd_clean(args.apply)
    if args.command == "ontology":
        return cmd_ontology_check(args.arquivo)
    if args.command == "gold":
        if args.gold_command == "fill-offsets":
            return gold_cli.cmd_fill_offsets(
                args.gold, args.canonical, args.out, args.report, PROCESSED_DIR
            )
        if args.gold_command == "convert-draft":
            return gold_cli.cmd_convert_draft(
                args.draft, args.canonical, args.out, args.report, PROCESSED_DIR
            )
        return gold_cli.cmd_validate(args.gold, args.canonical, PROCESSED_DIR)
    parser.error(f"comando desconhecido: {args.command}")


if __name__ == "__main__":
    sys.exit(main())

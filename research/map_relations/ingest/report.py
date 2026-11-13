"""Relatório de revisão humana da ingestão.

Gera canonical.txt, ingest.json e report.md dentro da pasta do documento
(data/processed/<hash_do_arquivo>/ — ADR 008). Nada disso vai para o Git.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from map_relations.core.ingest_contract import IngestResult, ParagraphKind

_FIRST_LINE_CHARS = 120


def _first_content_line(result: IngestResult, chapter: int) -> str:
    for p in result.paragraphs:
        if p.chapter == chapter and p.kind is ParagraphKind.texto:
            return result.text[p.start_offset : p.end_offset][:_FIRST_LINE_CHARS]
    return "(capítulo sem parágrafos de texto)"


def render_report(result: IngestResult) -> str:
    q = result.quality
    lines = [
        f"# Relatório de ingestão — {result.source.title}",
        "",
        f"- hash: `{result.source.content_hash}`",
        f"- páginas: {q.pages}",
        f"- parágrafos: {q.paragraphs}",
        f"- capítulos detectados: {q.chapters_detected}",
        "",
        "## Capítulos detectados",
        "",
    ]
    if result.chapters:
        for ch in result.chapters:
            lines.append(f"### cap. {ch.index} — {ch.title}")
            lines.append("")
            lines.append(f"> {_first_content_line(result, ch.index)}")
            lines.append("")
    else:
        lines.extend(["(nenhum)", ""])

    lines.extend(["## Itens removidos por página", ""])
    if result.removed:
        by_page: dict[int, list[str]] = defaultdict(list)
        for item in result.removed:
            desc = f"{item.reason.value}" + (f": {item.text}" if item.text else "")
            by_page[item.page].append(desc)
        lines.append("| Página | Itens removidos |")
        lines.append("|--------|-----------------|")
        for page in sorted(by_page):
            lines.append(f"| {page} | {'; '.join(by_page[page])} |")
    else:
        lines.append("(nenhum)")
    lines.append("")

    lines.extend(["## Alertas", ""])
    if q.alerts:
        lines.extend(f"- {alert}" for alert in q.alerts)
    else:
        lines.append("(nenhum)")
    lines.append("")
    return "\n".join(lines)


def write_processed(result: IngestResult, out_dir: Path) -> Path:
    """Grava os derivados (canonical.txt, ingest.json, report.md) em out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "canonical.txt").write_text(result.text, encoding="utf-8")
    (out_dir / "ingest.json").write_text(
        result.model_dump_json(by_alias=True, exclude={"text"}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "report.md").write_text(render_report(result), encoding="utf-8")
    return out_dir

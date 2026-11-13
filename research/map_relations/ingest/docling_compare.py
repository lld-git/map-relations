"""Compara a saída do Docling com o pdf_loader (prova do B04b).

Lê o JSON do DoclingDocument gerado pelo serviço docling e o IngestResult do
pdf_loader sobre o mesmo PDF, e produz um relatório Markdown para revisão
humana. Ligações incertas são marcadas com "?" — nada aqui decide sozinho;
a regra de aceite do Docling (v1-5) será medida contra o gabarito no B04b.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from map_relations.core.ingest_contract import IngestResult

from .canonical import _despace, is_explicit_heading

# labels do DoclingDocument que interessam à comparação
_HEADER_LABELS = {"title", "section_header"}
_PAGE_EDGE_LABELS = {"page_header", "page_footer"}


def load_docling_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _docling_texts(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Itens de texto com label, texto e páginas (defensivo a variações)."""
    items = []
    for t in doc.get("texts", []):
        pages = sorted(
            {p.get("page_no") for p in t.get("prov", []) if p.get("page_no")}
        )
        items.append(
            {"label": t.get("label", "?"), "text": (t.get("text") or "").strip(), "pages": pages}
        )
    return items


def _norm_title(text: str) -> str:
    return _despace(" ".join(text.split())).casefold()


def compare(result: IngestResult, doc: dict[str, Any]) -> str:
    items = _docling_texts(doc)
    headers = [i for i in items if i["label"] in _HEADER_LABELS and i["text"]]
    edges = [i for i in items if i["label"] in _PAGE_EDGE_LABELS and i["text"]]
    body = [i for i in items if i["label"] not in _PAGE_EDGE_LABELS]

    chapter_titles = {_norm_title(c.title) for c in result.chapters}
    explicit_headers = [h for h in headers if is_explicit_heading(h["text"])]
    other_headers = [h for h in headers if not is_explicit_heading(h["text"])]

    first_chapter_page = min(
        (h["pages"][0] for h in explicit_headers if h["pages"]), default=None
    )
    front_matter = (
        [i for i in body if i["pages"] and i["pages"][0] < first_chapter_page]
        if first_chapter_page
        else []
    )

    canonical = result.text
    remaining_edges = sorted(
        {e["text"] for e in edges if " ".join(e["text"].split()) in canonical}
    )

    crossing = [i for i in body if len(i["pages"]) > 1 and i["label"] == "text"]

    q = result.quality
    upper_alerts = sum("título em maiúsculas" in a for a in q.alerts)
    docling_paragraphs = len([i for i in body if i["label"] == "text"])
    removed_total = sum(q.removed_by_reason.values())
    lines = [
        f"# Comparação Docling × pdf_loader — {result.source.title}",
        "",
        f"- hash do canônico: `{result.source.content_hash}`",
        "",
        "| Medida | pdf_loader | Docling |",
        "|---|---|---|",
        f"| Capítulos / títulos explícitos | {q.chapters_detected} | {len(explicit_headers)} |",
        f"| Outros títulos (subtítulos) | {upper_alerts} (via alerta) | {len(other_headers)} |",
        f"| Parágrafos / blocos de texto | {q.paragraphs} | {docling_paragraphs} |",
        f"| Cabeçalho/rodapé identificados | {removed_total} (removidos) | {len(edges)} |",
        "",
        "## Títulos explícitos (Docling)",
        "",
    ]
    for h in explicit_headers:
        match = (
            "✓ casa com capítulo do pdf_loader"
            if _norm_title(h["text"]) in chapter_titles
            else "? sem par no pdf_loader"
        )
        page = h["pages"][0] if h["pages"] else "?"
        lines.append(f'- p.{page}: "{h["text"][:70]}" — {match}')
    if not explicit_headers:
        lines.append("(nenhum)")

    lines.extend(["", "## Subtítulos e seções (Docling, não explícitos)", ""])
    for h in other_headers[:30]:
        lines.append(f"- p.{h['pages'][0] if h['pages'] else '?'}: \"{h['text'][:70]}\"")
    if not other_headers:
        lines.append("(nenhum)")

    lines.extend(["", "## Folha de rosto / sumário (antes do primeiro capítulo)", ""])
    if first_chapter_page is None:
        lines.append("? Docling não encontrou título explícito — não dá para delimitar")
    elif front_matter:
        lines.append(
            f"{len(front_matter)} itens nas páginas 1–{first_chapter_page - 1} "
            f"(o pdf_loader manda tudo para o preâmbulo):"
        )
        for i in front_matter[:15]:
            lines.append(f"- p.{i['pages'][0]} [{i['label']}]: \"{i['text'][:60]}\"")
    else:
        lines.append("(nenhum item antes do primeiro capítulo)")

    lines.extend(["", "## Cabeçalhos/rodapés restantes no texto canônico", ""])
    if remaining_edges:
        lines.append(
            f"{len(remaining_edges)} textos que o Docling rotula como cabeçalho/rodapé "
            "ainda aparecem no canônico do pdf_loader:"
        )
        lines.extend(f"- \"{t[:70]}\"" for t in remaining_edges[:15])
    else:
        lines.append("nenhum — a remoção por repetição cobriu o que o Docling rotulou")

    lines.extend(["", "## Parágrafos que atravessam página (Docling)", ""])
    if crossing:
        lines.append(
            f"{len(crossing)} blocos de texto em mais de uma página — o pdf_loader "
            "divide esses em dois (exceto quando há hífen):"
        )
        for i in crossing[:10]:
            lines.append(f"- p.{'–'.join(map(str, i['pages']))}: \"{i['text'][:60]}…\"")
    else:
        lines.append("(nenhum)")

    lines.extend(
        [
            "",
            "## Alertas do pdf_loader",
            "",
            *(f"- {a}" for a in q.alerts),
            "",
        ]
    )
    return "\n".join(lines)

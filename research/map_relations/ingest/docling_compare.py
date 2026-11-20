"""Compara a saída de um conversor registrado com o pdf_loader (B04b;
generalizado para qualquer conversor no B04d fase 6).

Lê o JSON do DoclingDocument gerado pelo serviço docling (ou, depois do
B04d, qualquer `LayoutItem[]` da camada comum — `ingest/layout.py`) e o
IngestResult do pdf_loader sobre o mesmo PDF, e produz um relatório
Markdown para revisão humana. Ligações incertas são marcadas com "?" —
nada aqui decide sozinho; a regra de aceite do Docling (v1-5) será medida
contra o gabarito no B02.

B04d fase 6: `compare` deixou de ler o JSON nativo do Docling direto
(`label`, `prov`) e passa a operar sobre `LayoutItem[]` — a mesma
representação comum de `convert_docling.merged_layout_items` e
`canonical.layout_items` —, para `make compare` funcionar com qualquer
conversor registrado (ver `CONVERTERS` em `__main__.py`), não só Docling.
A seção "parágrafos que atravessam página" saiu: depois do B04c/B04d essa
junção já acontece na camada comum (`join_crossing_items`) antes de
`compare` ver os itens, então não há mais o que reportar aqui — cada
conversor já chega com o parágrafo unido ou não, conforme sua própria
regra."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from map_relations.core.ingest_contract import IngestResult

from .canonical import _despace, is_explicit_heading
from .layout import LayoutItem, LayoutLabel

_PAGE_EDGE_LABELS = {LayoutLabel.cabecalho, LayoutLabel.rodape}


def load_docling_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm_title(text: str) -> str:
    return _despace(" ".join(text.split())).casefold()


def compare(result: IngestResult, items: list[LayoutItem], converter: str = "Docling") -> str:
    headers = [i for i in items if i.label is LayoutLabel.titulo and i.text]
    edges = [i for i in items if i.label in _PAGE_EDGE_LABELS and i.text]
    body = [i for i in items if i.label not in _PAGE_EDGE_LABELS]

    chapter_titles = {_norm_title(c.title) for c in result.chapters}
    explicit_headers = [h for h in headers if is_explicit_heading(h.text)]
    other_headers = [h for h in headers if not is_explicit_heading(h.text)]

    first_chapter_page = min((h.page for h in explicit_headers if h.page), default=None)
    front_matter = (
        [i for i in body if i.page and i.page < first_chapter_page]
        if first_chapter_page
        else []
    )

    canonical = result.text
    remaining_edges = sorted(
        {e.text for e in edges if " ".join(e.text.split()) in canonical}
    )

    q = result.quality
    upper_alerts = sum("título em maiúsculas" in a for a in q.alerts)
    other_paragraphs = len([i for i in body if i.label is LayoutLabel.texto])
    removed_total = sum(q.removed_by_reason.values())
    lines = [
        f"# Comparação {converter} × pdf_loader — {result.source.title}",
        "",
        f"- hash do canônico: `{result.source.content_hash}`",
        "",
        f"| Medida | pdf_loader | {converter} |",
        "|---|---|---|",
        f"| Capítulos / títulos explícitos | {q.chapters_detected} | {len(explicit_headers)} |",
        f"| Outros títulos (subtítulos) | {upper_alerts} (via alerta) | {len(other_headers)} |",
        f"| Parágrafos / blocos de texto | {q.paragraphs} | {other_paragraphs} |",
        f"| Cabeçalho/rodapé identificados | {removed_total} (removidos) | {len(edges)} |",
        "",
        f"## Títulos explícitos ({converter})",
        "",
    ]
    for h in explicit_headers:
        match = (
            "✓ casa com capítulo do pdf_loader"
            if _norm_title(h.text) in chapter_titles
            else "? sem par no pdf_loader"
        )
        page = h.page if h.page else "?"
        lines.append(f'- p.{page}: "{h.text[:70]}" — {match}')
    if not explicit_headers:
        lines.append("(nenhum)")

    lines.extend(["", f"## Subtítulos e seções ({converter}, não explícitos)", ""])
    for h in other_headers[:30]:
        lines.append(f"- p.{h.page if h.page else '?'}: \"{h.text[:70]}\"")
    if not other_headers:
        lines.append("(nenhum)")

    lines.extend(["", "## Folha de rosto / sumário (antes do primeiro capítulo)", ""])
    if first_chapter_page is None:
        lines.append(f"? {converter} não encontrou título explícito — não dá para delimitar")
    elif front_matter:
        lines.append(
            f"{len(front_matter)} itens nas páginas 1–{first_chapter_page - 1} "
            f"(o pdf_loader manda tudo para o preâmbulo):"
        )
        for i in front_matter[:15]:
            lines.append(f"- p.{i.page} [{i.label.value}]: \"{i.text[:60]}\"")
    else:
        lines.append("(nenhum item antes do primeiro capítulo)")

    lines.extend(["", "## Cabeçalhos/rodapés restantes no texto canônico", ""])
    if remaining_edges:
        lines.append(
            f"{len(remaining_edges)} textos que o {converter} rotula como cabeçalho/rodapé "
            "ainda aparecem no canônico do pdf_loader:"
        )
        lines.extend(f"- \"{t[:70]}\"" for t in remaining_edges[:15])
    else:
        lines.append(f"nenhum — a remoção por repetição cobriu o que o {converter} rotulou")

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

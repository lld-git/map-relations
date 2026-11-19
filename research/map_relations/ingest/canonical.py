"""Rota pdf_loader da ingestão (fallback barato do Docling — ADR 008).

Converte páginas brutas de um parser em blocos MdBlock (com página, título e
alertas) para o Markdown intermediário. A montagem do IngestResult vive no
parser único (markdown.parse_markdown); build_ingest_result encadeia os dois.

B04d fase 3: adaptador para a camada comum (ingest/layout.py). A remoção de
cabeçalho/rodapé/número de página (antes `_find_repeated_edges` + a parte de
decisão de `_clean_pages`) passa a ser `layout.drop_page_furniture`, operando
sobre a primeira/última linha não vazia de cada página como `LayoutItem`
(mesmo critério de borda de antes). A junção de parágrafo que atravessa
página (antes um `if ... endswith("-")` ad hoc em `pdf_pages_to_blocks`) passa
a ser `layout.join_crossing_items`, a mesma função da fase 2.1 — aqui a
fronteira é entre páginas em vez de entre faixas do Docling.
`classify_headings` continua à parte (não migra para `layout.classify_titles`):
as mensagens de alerta do pdf_loader ("título em maiúsculas…", "…regra de
maiúsculas…") são diferentes, literalmente, das do Docling ("título do
layout…", "…layout do Docling…" — ver plano B04d B.4.2), e `test_ingest_contract`
confere o texto do pdf_loader; unificar os dois é trabalho de outro bloco.
"""

from __future__ import annotations

import re

from map_relations.core.ingest_contract import (
    IngestResult,
    ParagraphKind,
    RemovalReason,
    RemovedItem,
)

from .layout import (  # noqa: F401 (despace/is_explicit_heading re-exportados: docling_compare, alerts)
    LayoutItem,
    LayoutLabel,
    _despace,
    drop_page_furniture,
    is_explicit_heading,
    join_crossing_items,
    renumber,
)
from .markdown import MdBlock, parse_markdown, render_markdown


def _is_uppercase_heading(line: str) -> bool:
    """Linha curta toda em maiúsculas — candidata a título, menos confiável."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    letters = [c for c in line if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and len(line) >= 3


def _is_chapter_heading(line: str) -> bool:
    return is_explicit_heading(line) or _is_uppercase_heading(line)


def classify_headings(texts: list[str]) -> tuple[list[bool], list[str]]:
    """Precedência de títulos (genérica, sem regra de livro específico):
    com títulos explícitos, só eles numeram capítulos — maiúsculas viram texto
    com alerta; sem nenhum explícito, maiúsculas numeram, com alerta."""
    explicit = [is_explicit_heading(t) for t in texts]
    upper_only = [_is_uppercase_heading(t) and not e for t, e in zip(texts, explicit)]
    alerts: list[str] = []
    if any(explicit):
        for text, up in zip(texts, upper_only):
            if up:
                alerts.append(
                    f'título em maiúsculas não numerado como capítulo: "{text[:60]}"'
                )
        return explicit, alerts
    if any(upper_only):
        alerts.append(
            "capítulos detectados apenas pela regra de maiúsculas — confirmar na revisão"
        )
    return [e or u for e, u in zip(explicit, upper_only)], alerts


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _border_items(
    pages_lines: list[list[str]],
) -> tuple[list[LayoutItem], dict[int, tuple[int, int]]]:
    """Primeira e última linha não vazia de cada página, como LayoutItem
    (uma entrada por borda; a mesma linha quando a página só tem uma).
    `positions` mapeia `order` de volta para (índice da página, índice da
    linha) — só assim dá para remover a linha certa depois, já que
    LayoutItem não carrega posição dentro da página, só `page`."""
    items: list[LayoutItem] = []
    positions: dict[int, tuple[int, int]] = {}
    order = 0
    for page_idx, lines in enumerate(pages_lines):
        idxs = [i for i, ln in enumerate(lines) if ln.strip()]
        if not idxs:
            continue
        for i in dict.fromkeys((idxs[0], idxs[-1])):  # dedupe preservando ordem
            items.append(
                LayoutItem(
                    order=order,
                    label=LayoutLabel.texto,
                    text=lines[i],
                    source_label="line",
                    converter="pdf_loader",
                    page=page_idx + 1,
                )
            )
            positions[order] = (page_idx, i)
            order += 1
    return items, positions


def _clean_pages(
    raw_pages: list[str],
) -> tuple[list[str], list[RemovedItem], list[str]]:
    """Remove cabeçalhos, rodapés e números de página das bordas de cada
    página (layout.drop_page_furniture, pela mesma regra de repetição de
    antes), preservando linhas em branco (estrutura de parágrafos)."""
    pages_lines = [page.splitlines() for page in raw_pages]
    removed: list[RemovedItem] = []
    alerts: list[str] = []

    for page_idx, lines in enumerate(pages_lines):
        if not any(ln.strip() for ln in lines):
            removed.append(
                RemovedItem(
                    page=page_idx + 1, reason=RemovalReason.pagina_vazia, text=""
                )
            )
            alerts.append(f"página {page_idx + 1} sem texto")

    items, positions = _border_items(pages_lines)
    kept, border_removed, _ = drop_page_furniture(items)
    removed.extend(border_removed)

    drop_by_page: dict[int, set[int]] = {}
    for order in {it.order for it in items} - {it.order for it in kept}:
        page_idx, line_idx = positions[order]
        drop_by_page.setdefault(page_idx, set()).add(line_idx)

    cleaned: list[str] = []
    for page_idx, lines in enumerate(pages_lines):
        if not any(ln.strip() for ln in lines):
            cleaned.append("")
            continue
        drop = drop_by_page.get(page_idx, set())
        cleaned.append(
            "\n".join(ln for i, ln in enumerate(lines) if i not in drop).strip("\n")
        )
    return cleaned, removed, alerts


def _split_paragraph_blocks(text: str) -> list[str]:
    text = re.sub(r"-\n", "", text)         # junta palavras hifenizadas
    text = re.sub(r"[^\S\n]+", " ", text)   # colapsa espaços, preserva \n
    # títulos de capítulo viram blocos próprios mesmo sem linha em branco
    isolated: list[str] = []
    for line in text.split("\n"):
        if _is_chapter_heading(line):
            isolated.extend(["", line.strip(), ""])
        else:
            isolated.append(line)
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(isolated))
    blocks = []
    for block in text.split("\n\n"):
        # \n interno vira espaço: cada parágrafo canônico é uma linha
        flat = _normalize_line(block.replace("\n", " "))
        if flat:
            blocks.append(flat)
    return blocks


def _page_items(cleaned_pages: list[str]) -> list[list[LayoutItem]]:
    """Cada página limpa → seus parágrafos (`_split_paragraph_blocks`, que
    faz desifenização, colapso de espaço e isolamento de título — é
    texto→itens, não pós-processamento) como `LayoutItem` com `page`, sem
    `bbox`. Uma sublista por página, para `join_crossing_items` enxergar a
    fronteira entre páginas (o mesmo papel que a fronteira entre faixas do
    Docling)."""
    ranges: list[list[LayoutItem]] = []
    order = 0
    for page_no, page in enumerate(cleaned_pages, start=1):
        items: list[LayoutItem] = []
        for text in _split_paragraph_blocks(page) if page else []:
            items.append(
                LayoutItem(
                    order=order,
                    label=LayoutLabel.texto,
                    text=text,
                    source_label="paragraph",
                    converter="pdf_loader",
                    page=page_no,
                )
            )
            order += 1
        ranges.append(items)
    return ranges


def pdf_pages_to_blocks(
    raw_pages: list[str],
) -> tuple[list[MdBlock], list[RemovedItem], list[str]]:
    """Conversor fallback: páginas brutas → blocos MdBlock com página.

    Mantém o comportamento histórico do pdf_loader: quebra de página é quebra
    de bloco, exceto quando a página termina com hífen (palavra atravessa) —
    agora via layout.join_crossing_items, a mesma regra da rota Docling."""
    cleaned_pages, removed, alerts = _clean_pages(raw_pages)

    merged = renumber(join_crossing_items(_page_items(cleaned_pages)))
    blocks = [MdBlock(it.text, page=it.page) for it in merged]

    is_heading, heading_alerts = classify_headings([b.text for b in blocks])
    for block, heading in zip(blocks, is_heading):
        if heading:
            block.kind = ParagraphKind.titulo
    alerts.extend(heading_alerts)
    return blocks, removed, alerts


def build_ingest_result(raw_pages: list[str], title: str, kind: str) -> IngestResult:
    """Rota pdf_loader completa: páginas → MdBlocks → documento.md → parser único."""
    blocks, removed, alerts = pdf_pages_to_blocks(raw_pages)
    md = render_markdown(blocks)
    return parse_markdown(
        md, title, kind, removed=removed, extra_alerts=alerts, pages=len(raw_pages)
    )

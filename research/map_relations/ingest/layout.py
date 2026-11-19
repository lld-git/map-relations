"""Camada comum de layout entre conversores (B04d, Opção B).

LayoutItem é a representação de passagem entre a saída nativa de um
conversor (Docling, pdf_loader, TXT, pandoc, e no futuro MinerU) e os
MdBlocks do Markdown intermediário. É estrutura interna: dataclass, não
Pydantic, nada daqui vai para contracts/schemas. Um item é imutável; as
regras de pós-processamento produzem listas novas (dataclasses.replace).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, replace


class LayoutLabel(enum.StrEnum):
    """Rótulo normalizado de um item de layout (entrada da classificação,
    distinto de ParagraphKind, que só o pós-processamento decide)."""

    titulo = "titulo"
    texto = "texto"
    lista = "lista"
    cabecalho = "cabecalho"
    rodape = "rodape"
    numero_pagina = "numero_pagina"
    tabela = "tabela"
    figura = "figura"
    nota = "nota"
    desconhecido = "desconhecido"


@dataclass(frozen=True)
class BBox:
    """Caixa normalizada: fração da página (0.0–1.0), origem no topo-esquerda."""

    top: float
    bottom: float
    left: float
    right: float


@dataclass(frozen=True)
class LayoutItem:
    """Item de layout, já traduzido para o vocabulário comum. Imutável."""

    order: int
    label: LayoutLabel
    text: str
    source_label: str
    converter: str
    page: int | None = None
    bbox: BBox | None = None
    marker: str | None = None
    level: int | None = None
    furniture_hint: bool = False


def normalize_bbox(
    left: float,
    top: float,
    right: float,
    bottom: float,
    page_width: float,
    page_height: float,
) -> BBox:
    """Normaliza uma bbox do Docling (coord_origin BOTTOMLEFT, pontos PDF)
    para fração da página com origem no topo-esquerda. `top`/`bottom` chegam
    em coordenadas de origem inferior (top > bottom); o eixo vertical é
    invertido aqui e cada medida é dividida pelo tamanho da própria página,
    para páginas de tamanhos diferentes no mesmo documento produzirem
    frações comparáveis."""
    return BBox(
        top=(page_height - top) / page_height,
        bottom=(page_height - bottom) / page_height,
        left=left / page_width,
        right=right / page_width,
    )


def resolve_label(
    source_label: str, mapping: dict[str, LayoutLabel]
) -> tuple[LayoutLabel, str | None]:
    """Traduz um rótulo nativo para LayoutLabel via `mapping`. Rótulo ausente
    do mapa nunca é descartado em silêncio: vira `desconhecido` com alerta,
    para uma versão nova do conversor aparecer na revisão em vez de
    desaparecer."""
    label = mapping.get(source_label)
    if label is None:
        return (
            LayoutLabel.desconhecido,
            f'rótulo desconhecido do conversor: "{source_label}"',
        )
    return label, None


def renumber(items: list[LayoutItem]) -> list[LayoutItem]:
    """Renumera `order` para 0-based contíguo. Única fonte de ordem: depois
    de juntar faixas, nenhuma regra pode depender da posição na lista
    original, só do campo `order`."""
    return [replace(it, order=i) for i, it in enumerate(items)]


# pontuação que encerra parágrafo: se o item anterior termina assim, não é
# continuação de um parágrafo cortado na fronteira de uma faixa/página.
_SENTENCE_END = (".", "!", "?", ":", ";", '"', "»", ")", "]", "…")


def _continues_paragraph(prev: str, nxt: str) -> bool:
    """O item anterior parece um parágrafo cortado que segue no próximo?"""
    if not prev or not nxt:
        return False
    if prev.endswith("-"):
        return True
    return not prev.endswith(_SENTENCE_END) and nxt[:1].islower()


def _join_paragraph(prev: str, nxt: str) -> str:
    if prev.endswith("-"):
        return prev[:-1] + nxt  # palavra hifenizada atravessa a fronteira
    return f"{prev} {nxt}"


def join_crossing_items(ranges: list[list[LayoutItem]]) -> list[LayoutItem]:
    """Junta o item de texto cortado na fronteira entre faixas consecutivas
    (página sem pontuação final seguida de minúscula, ou hífen) — só entre
    faixas; itens dentro da mesma faixa não são tocados. Nunca junta quando
    um dos lados é título: o sinal (`LayoutLabel.texto` nos dois lados) já
    garante isso, porque um título nunca tem esse rótulo."""
    merged: list[LayoutItem] = []
    for items in ranges:
        if merged and items:
            prev, nxt = merged[-1], items[0]
            if (
                prev.label is LayoutLabel.texto
                and nxt.label is LayoutLabel.texto
                and _continues_paragraph(prev.text, nxt.text)
            ):
                merged[-1] = replace(prev, text=_join_paragraph(prev.text, nxt.text))
                items = items[1:]
        merged.extend(items)
    return merged

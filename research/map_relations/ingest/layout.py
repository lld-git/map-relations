"""Camada comum de layout entre conversores (B04d, Opção B).

LayoutItem é a representação de passagem entre a saída nativa de um
conversor (Docling, pdf_loader, TXT, pandoc, e no futuro MinerU) e os
MdBlocks do Markdown intermediário. É estrutura interna: dataclass, não
Pydantic, nada daqui vai para contracts/schemas. Um item é imutável; as
regras de pós-processamento produzem listas novas (dataclasses.replace).
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, replace

from map_relations.core.ingest_contract import ParagraphKind


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


# Padrões explícitos de capítulo (com e sem espaçamento entre letras). Único
# sinal forte de título entre todos os conversores: quando presente em
# qualquer item do documento, só ele numera capítulos (ver classify_titles).
_CHAPTER_RES = [
    re.compile(r"^cap[íi]tulo\s+\S+", re.IGNORECASE),
    re.compile(r"^[IVXLCDM]{1,7}\.?$"),
]
# Versões sobre o texto sem espaços ("C A P Í T U L O I" → "capítuloi").
_CHAPTER_DESPACED_RES = [
    re.compile(r"^cap[íi]tulo", re.IGNORECASE),
    re.compile(r"^[IVXLCDM]{1,7}\.?$", re.IGNORECASE),
]


def _despace(line: str) -> str:
    """Remove espaçamento tipográfico entre letras, para detecção apenas.
    Só age quando a maioria dos tokens é de um caractere (letras espaçadas)."""
    tokens = line.split()
    if len(tokens) >= 4 and sum(len(t) == 1 for t in tokens) / len(tokens) >= 0.7:
        return "".join(tokens)
    return line


def is_explicit_heading(line: str) -> bool:
    """Título que casa um padrão explícito de capítulo (Capítulo N, romanos),
    inclusive com letras espaçadas."""
    line = line.strip()
    if not line or len(line) > 60:
        return False
    if any(rx.match(line) for rx in _CHAPTER_RES):
        return True
    despaced = _despace(line)
    return despaced != line and any(rx.match(despaced) for rx in _CHAPTER_DESPACED_RES)


def classify_titles(items: list[LayoutItem]) -> tuple[list[ParagraphKind], list[str]]:
    """Precedência de títulos sobre LayoutItem[], genérica entre conversores
    que já produzem um sinal fraco de título via `label is LayoutLabel.titulo`
    (hoje só o Docling; a rota pdf_loader ainda decide por conta própria —
    ver canonical.classify_headings — até migrar para a camada comum).

    Título explícito (is_explicit_heading) é sinal forte: com algum presente
    no documento, só eles numeram capítulos. Sinal fraco do layout sem
    explícito por perto vira texto com alerta; logo depois de um título,
    promove a subtítulo. Sem nenhum explícito, o sinal fraco numera, com
    alerta-resumo."""
    kinds: list[ParagraphKind] = []
    alerts: list[str] = []
    has_explicit = any(is_explicit_heading(it.text) for it in items)
    previous_was_title = False
    for it in items:
        if is_explicit_heading(it.text):
            kinds.append(ParagraphKind.titulo)
            previous_was_title = True
            continue
        if it.label is LayoutLabel.titulo:
            if not has_explicit:
                kinds.append(ParagraphKind.titulo)
                previous_was_title = True
                continue
            if previous_was_title:
                kinds.append(ParagraphKind.subtitulo)
                previous_was_title = False
                continue
            alerts.append(f'título do layout não numerado como capítulo: "{it.text[:60]}"')
        kinds.append(ParagraphKind.texto)
        previous_was_title = False

    if not has_explicit and any(it.label is LayoutLabel.titulo for it in items):
        alerts.append(
            "capítulos vindos só do layout do Docling — confirmar na revisão"
        )
    return kinds, alerts

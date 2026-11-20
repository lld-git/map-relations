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
from collections import Counter
from dataclasses import dataclass, replace

from map_relations.core.ingest_contract import ParagraphKind, RemovalReason, RemovedItem


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

# travessão de fala: o próximo item que abre com um destes nunca é
# continuação do anterior, mesmo sem pontuação final (decisão do E2, B04d).
_DASH_PREFIXES = ("-", "–", "—")


def _continues_paragraph(prev: str, nxt: str) -> bool:
    """O item anterior parece um parágrafo cortado que segue no próximo?

    Decisão do E2 (B04d): bloco sem pontuação final une ao seguinte mesmo
    que ele comece com maiúscula (nome próprio, como "K." no início de
    página) — a maiúscula deixou de ser condição. Exceções: o seguinte
    começa com travessão de fala, ou é título/item de lista (já excluído
    pelo guard de `label` em `join_crossing_items`); o anterior ser título
    também já é excluído pelo mesmo guard."""
    if not prev or not nxt:
        return False
    if prev.endswith("-"):
        return True
    if nxt.startswith(_DASH_PREFIXES):
        return False
    return not prev.endswith(_SENTENCE_END)


def _join_paragraph(prev: str, nxt: str) -> str:
    if prev.endswith("-"):
        return prev[:-1] + nxt  # palavra hifenizada atravessa a fronteira
    return f"{prev} {nxt}"


def join_crossing_items(ranges: list[list[LayoutItem]]) -> list[LayoutItem]:
    """Junta o item de texto cortado na fronteira entre faixas consecutivas
    (página sem pontuação final, ou hífen — ver `_continues_paragraph`,
    decisão do E2) — só entre faixas; itens dentro da mesma faixa não são
    tocados. Nunca junta quando um dos lados é título ou item de lista: o
    sinal (`LayoutLabel.texto` nos dois lados) já garante isso, porque
    título e lista nunca têm esse rótulo."""
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


# Linha repetida no início/fim de pelo menos esta fração das páginas é
# tratada como cabeçalho/rodapé.
_REPEAT_THRESHOLD = 0.6

_PAGE_NUMBER_RE = re.compile(r"^[\s\-–—]*\d{1,4}[\s\-–—]*$")


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _page_edges(items: list[LayoutItem]) -> dict[int, tuple[LayoutItem, LayoutItem]]:
    """Primeiro e último item de cada página, por `order` dentro da página
    (não pela posição na lista — única fonte de ordem é o campo `order`)."""
    by_page: dict[int, list[LayoutItem]] = {}
    for it in items:
        if it.page is not None:
            by_page.setdefault(it.page, []).append(it)
    edges = {}
    for page, page_items in by_page.items():
        ordered = sorted(page_items, key=lambda it: it.order)
        edges[page] = (ordered[0], ordered[-1])
    return edges


def drop_page_furniture(
    items: list[LayoutItem],
) -> tuple[list[LayoutItem], list[RemovedItem], list[str]]:
    """Remove cabeçalho/rodapé repetidos e número de página das bordas de
    cada página (primeiro/último item por `page` + `order`), pela mesma
    regra de repetição entre páginas de antes — generalizada para operar
    sobre LayoutItem em vez de "primeira/última linha da lista" de uma
    página em `list[str]`. Itens sem página (`page is None`) nunca são
    tocados: não há borda de página para eles."""
    edges = _page_edges(items)
    removed: list[RemovedItem] = []
    alerts: list[str] = []
    if len(edges) < 3:
        return list(items), removed, alerts

    threshold = max(2, int(len(edges) * _REPEAT_THRESHOLD))
    tops = Counter(_normalize_line(first.text) for first, _ in edges.values())
    bottoms = Counter(_normalize_line(last.text) for _, last in edges.values())
    headers = {line for line, n in tops.items() if n >= threshold and line}
    footers = {line for line, n in bottoms.items() if n >= threshold and line}

    drop_ids: set[int] = set()  # por `order`, que é único no documento
    for page, (first, last) in edges.items():
        norm_first = _normalize_line(first.text)
        norm_last = _normalize_line(last.text)
        if norm_first in headers:
            drop_ids.add(first.order)
            removed.append(RemovedItem(page=page, reason=RemovalReason.cabecalho, text=norm_first))
        if last is not first and norm_last in footers:
            drop_ids.add(last.order)
            removed.append(RemovedItem(page=page, reason=RemovalReason.rodape, text=norm_last))
        for candidate in dict.fromkeys((first, last)):  # dedupe preservando ordem
            norm = _normalize_line(candidate.text)
            if candidate.order not in drop_ids and _PAGE_NUMBER_RE.match(norm):
                drop_ids.add(candidate.order)
                removed.append(
                    RemovedItem(page=page, reason=RemovalReason.numero_pagina, text=norm)
                )

    kept = [it for it in items if it.order not in drop_ids]
    return kept, removed, alerts


@dataclass(frozen=True)
class BodyBand:
    """Faixa vertical típica do corpo do documento, em fração de página
    (mesma convenção de BBox: topo-esquerda, 0.0–1.0). `confident` é False
    quando não há bbox suficiente de itens de corpo — poucas páginas ou
    nenhuma geometria — e a regra da faixa não deve decidir nesse caso
    (fallback: comportamento de antes da fase 5, ver `apply_body_band`)."""

    top: float
    bottom: float
    confident: bool


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


# Itens de corpo genuíno — nunca cabecalho/rodape, que é exatamente o que a
# regra da faixa decide; incluir esses dois enviesaria a própria medida.
_BODY_LABELS = {LayoutLabel.texto, LayoutLabel.titulo, LayoutLabel.lista}

# Mesmo limiar de "poucas páginas" do drop_page_furniture (len(edges) < 3).
_MIN_PAGES_FOR_BAND = 3


def _is_body_candidate(it: LayoutItem) -> bool:
    """Item de corpo genuíno para medir a faixa: rótulo de corpo, com bbox,
    e não um candidato a número de página — um número isolado na borda não
    representa a margem do corpo mesmo quando rotulado `texto` (é
    exatamente o caso que a regra da faixa precisa detectar, não usar
    como referência)."""
    return (
        it.label in _BODY_LABELS
        and it.bbox is not None
        and not _PAGE_NUMBER_RE.match(_normalize_line(it.text))
    )


def compute_body_band(items: list[LayoutItem]) -> BodyBand:
    """Faixa do corpo por percentis (5º/95º) das bboxes dos itens de corpo
    de TODO o documento passado — fase 5 (B04d): quando chamada depois do
    merge de faixas de página (B04c), o corte é um só sobre o documento
    inteiro, nunca um por faixa."""
    body_bboxes = [it.bbox for it in items if _is_body_candidate(it) and it.bbox is not None]
    pages_with_bbox = {it.page for it in items if _is_body_candidate(it) and it.page is not None}
    if len(pages_with_bbox) < _MIN_PAGES_FOR_BAND or not body_bboxes:
        return BodyBand(top=0.0, bottom=1.0, confident=False)
    return BodyBand(
        top=_percentile([b.top for b in body_bboxes], 0.05),
        bottom=_percentile([b.bottom for b in body_bboxes], 0.95),
        confident=True,
    )


def _within_band(bbox: BBox, band: BodyBand) -> bool:
    return bbox.top >= band.top and bbox.bottom <= band.bottom


# Rótulo de moldura → razão de remoção, no fallback (faixa não confiável ou
# item sem bbox): mesmo comportamento incondicional de antes da fase 5.
_FURNITURE_REASONS = {
    LayoutLabel.cabecalho: RemovalReason.cabecalho,
    LayoutLabel.rodape: RemovalReason.rodape,
}


def apply_body_band(
    items: list[LayoutItem], band: BodyBand | None = None
) -> tuple[list[LayoutItem], list[RemovedItem], list[str]]:
    """Regra nova da Opção A, só a fase 5 (B04d): item de cabeçalho/rodapé
    **dentro** da faixa do corpo volta a ser texto, na posição original;
    **fora** da faixa é removido; número de página fora da faixa é removido
    mesmo chegando com rótulo `text`, mas número **dentro** da faixa
    (citação no meio do parágrafo, por exemplo) é mantido.

    `band` é opcional: quando omitido, é calculada a partir dos próprios
    `items` (uso de faixa única); passar uma `BodyBand` já calculada sobre o
    documento inteiro é o que faz o corte valer para todas as faixas de
    página de uma vez (fase 5, nota do B04c).

    Sem faixa confiável, ou item individual sem bbox: comportamento de
    antes da fase 5 — cabecalho/rodapé sempre removidos, incondicional; o
    resto (inclusive número de página) intocado — com alerta quando a
    faixa inteira não é confiável, para a revisão humana confirmar."""
    if band is None:
        band = compute_body_band(items)

    kept: list[LayoutItem] = []
    removed: list[RemovedItem] = []
    alerts: list[str] = []

    if not band.confident:
        alerts.append("faixa do corpo não confiável — mantendo comportamento atual")
        for it in items:
            reason = _FURNITURE_REASONS.get(it.label)
            if reason is not None:
                removed.append(RemovedItem(page=it.page or 0, reason=reason, text=it.text))
            else:
                kept.append(it)
        return kept, removed, alerts

    for it in items:
        if it.bbox is None:
            reason = _FURNITURE_REASONS.get(it.label)
            if reason is not None:
                removed.append(RemovedItem(page=it.page or 0, reason=reason, text=it.text))
            else:
                kept.append(it)
            continue

        if _PAGE_NUMBER_RE.match(_normalize_line(it.text)) and not _within_band(it.bbox, band):
            removed.append(
                RemovedItem(page=it.page or 0, reason=RemovalReason.numero_pagina, text=it.text)
            )
            continue

        reason = _FURNITURE_REASONS.get(it.label)
        if reason is None:
            kept.append(it)
        elif _within_band(it.bbox, band):
            kept.append(replace(it, label=LayoutLabel.texto))
            alerts.append(
                f'{it.label.value} dentro da faixa do corpo volta a ser texto '
                f'(p.{it.page}): "{it.text[:60]}"'
            )
        else:
            removed.append(RemovedItem(page=it.page or 0, reason=reason, text=it.text))

    return kept, removed, alerts

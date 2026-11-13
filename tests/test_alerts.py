"""Resolução de alertas da conversão sobre o documento.md atual (ADR 008)."""

from map_relations.core.ingest_contract import ParagraphKind
from map_relations.ingest.alerts import classify_conversion_alerts
from map_relations.ingest.markdown import MdBlock, md_hash, render_markdown

GENERATED = render_markdown(
    [
        MdBlock("O PROCESSO", ParagraphKind.texto, page=1),
        MdBlock("C A P Í T U L O I A Visita. Conversa com Grubach", ParagraphKind.texto, page=4),
        MdBlock("Josef K. entrou na sala.", ParagraphKind.texto, page=4),
    ]
)

CONV_ALERTS = [
    "capítulos vindos só do layout do Docling — confirmar na revisão",
    'título do layout não numerado como capítulo: "O PROCESSO"',
]


def test_not_edited_keeps_all_active():
    out = classify_conversion_alerts(CONV_ALERTS, GENERATED, edited=False)
    assert [c.resolved for c in out] == [False, False]


def test_edited_resolves_when_not_reproduced():
    # revisão: cria capítulo explícito e remove o título de paratexto
    edited_md = render_markdown(
        [
            MdBlock("Nota de rosto", ParagraphKind.texto, page=1),
            MdBlock("CAPÍTULO I", ParagraphKind.titulo, page=4),
            MdBlock("A Visita. Conversa com Grubach", ParagraphKind.subtitulo, page=4),
            MdBlock("Josef K. entrou na sala.", ParagraphKind.texto, page=4),
        ]
    )
    out = classify_conversion_alerts(CONV_ALERTS, edited_md, edited=True)
    resolved = {c.message: c.resolved for c in out}
    # agora há capítulo explícito → alerta-resumo resolvido
    assert resolved["capítulos vindos só do layout do Docling — confirmar na revisão"]
    # "O PROCESSO" não é mais parágrafo de texto → detalhe resolvido
    assert resolved['título do layout não numerado como capítulo: "O PROCESSO"']


def test_edited_but_condition_persists_stays_active():
    # edição qualquer, mas sem capítulo explícito e com o trecho ainda presente
    edited_md = GENERATED + "\n\nParágrafo novo.\n"
    out = classify_conversion_alerts(CONV_ALERTS, edited_md, edited=True)
    resolved = {c.message: c.resolved for c in out}
    assert not resolved["capítulos vindos só do layout do Docling — confirmar na revisão"]
    assert not resolved['título do layout não numerado como capítulo: "O PROCESSO"']


def test_md_hash_detects_edit():
    assert md_hash(GENERATED) == md_hash(GENERATED)
    assert md_hash(GENERATED) != md_hash(GENERATED + "\n\nx\n")

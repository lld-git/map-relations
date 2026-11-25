"""Cenário sintético do `eval` (B02 §7): canônico, gabarito e execução inventados.

Nenhum trecho de obra protegida entra aqui. Os números esperados estão
calculados à mão em tests/test_eval.py.
"""

from __future__ import annotations

from typing import Any

from map_relations.core.ingest_contract import IngestResult
from map_relations.evaluation.gold import GoldRelation, relation_id
from map_relations.ingest.markdown import parse_markdown
from map_relations.ontology_io import load_ontology

ONTOLOGY = load_ontology()

MD = (
    "# Capítulo I\n\n"
    "Ana vigiava Bruno todos os dias, de manhã e de noite, sem explicar nada a ninguém.\n\n"
    "Carla disse que a chave velha estava na gaveta. Depois Ana guardou a chave velha no bolso.\n\n"
    "# Capítulo II\n\n"
    "Bruno respondeu que a chave velha sumiu de novo. Carla riu da resposta dele.\n\n"
    "# Capítulo III\n\n"
    "Fulano gritou na rua sem motivo nenhum, e Dora assistiu em silêncio.\n"
)

# trechos (únicos no texto) usados como evidência
Q_VIGIA = "Ana vigiava Bruno todos os dias"  # cap. 1
Q_CARLA = "Carla disse que a chave velha estava na gaveta"  # cap. 1
Q_BOLSO = "Depois Ana guardou a chave velha no bolso"  # cap. 1
Q_BRUNO = "Bruno respondeu que a chave velha sumiu de novo"  # cap. 2
Q_FULANO = "Fulano gritou na rua sem motivo nenhum"  # cap. 3


def make_canon() -> IngestResult:
    return parse_markdown(MD, title="sintetico", kind="txt")


def span(canon: IngestResult, exact: str) -> tuple[int, int]:
    assert canon.text.count(exact) == 1, exact
    start = canon.text.index(exact)
    return start, start + len(exact)


def _anchor(canon: IngestResult, exact: str) -> dict[str, Any]:
    s, e = span(canon, exact)
    return {
        "exact": exact,
        "prefix": canon.text[max(0, s - 32) : s],
        "suffix": canon.text[e : e + 32],
        "startOffset": s,
        "endOffset": e,
    }


def gev(canon: IngestResult, exact: str, chapter: str, support: str = "alto") -> dict[str, Any]:
    return {
        "chapter": chapter,
        "anchor": _anchor(canon, exact),
        "support": support,
        "polarity": "apoia",
    }


def _rel(canon: IngestResult, **kw: Any) -> dict[str, Any]:
    rel = {
        "class": "afirmada",
        "narrative_scope": "obra",
        "origin": "humano",
        **kw,
    }
    rel["id"] = relation_id(GoldRelation.model_validate({**rel, "id": "x"}), ONTOLOGY)
    return rel


def make_gold(canon: IngestResult) -> dict[str, Any]:
    """Cinco positivos provados no escopo `obra`, um sem prova, um encaixado, um fictício."""
    relations = [
        # G1
        _rel(canon, subject="ana", type="exerce_vigilancia_sobre", object="bruno",
             evidence=[gev(canon, Q_VIGIA, "1")]),
        # G2: alegada por bruno
        _rel(canon, subject="carla", type="exerce_coercao_sobre", object="ana",
             **{"class": "alegada"}, asserted_by="bruno",
             evidence=[gev(canon, Q_CARLA, "1")]),
        # G3: simétrica
        _rel(canon, subject="ana", type="amizade_com", object="carla",
             evidence=[gev(canon, Q_BOLSO, "1")]),
        # G4: o extrator vai acertar só o tipo pai (age_em_nome_de)
        _rel(canon, subject="bruno", type="representa_juridicamente", object="carla",
             evidence=[gev(canon, Q_BRUNO, "2")]),
        # G5: texto encaixado
        _rel(canon, subject="ana", type="vinculo_amoroso_com", object="bruno",
             narrative_scope="texto_encaixado", evidence=[gev(canon, Q_CARLA, "1")]),
        # G6: sem prova (só evidência baixa, sem conjunto): ignorada
        _rel(canon, subject="carla", type="adversario_de", object="bruno",
             evidence=[gev(canon, Q_BOLSO, "1", support="baixo")]),
        # G7: provada em conjunto (duas evidências médias)
        _rel(canon, subject="ana", type="adversario_de", object="bruno",
             provas_em_conjunto="suficiente",
             evidence=[gev(canon, Q_VIGIA, "1", support="medio"),
                       gev(canon, Q_BRUNO, "2", support="medio")]),
        # fictícia: a âncora não existe no canônico e não é conferida
        _rel(canon, subject="ana", type="amizade_com", object="fic_exemplo", fictional=True,
             evidence=[{"chapter": "1", "support": "alto", "polarity": "apoia",
                        "anchor": {"exact": "texto fictício", "prefix": "", "suffix": "",
                                   "startOffset": 0, "endOffset": 14}}]),
    ]  # fmt: skip
    for rel in relations:
        rel.setdefault("origin_detail", None)
    return {
        "schema_version": 1,
        "work": "Obra Sintética",
        "source": {
            "content_hash": "sha256:" + canon.source.content_hash,
            "offset_unit": "codepoint_nfc",
            "end": "exclusive",
        },
        "ontology_version": ONTOLOGY.version,
        "scope": {"chapters": ["1", "2"], "narrative_scopes_evaluated": ["obra"]},
        "annotation_rules": [],
        "entities": [
            {"id": "ana", "preferredName": "Ana", "aliases": ["a vizinha"]},
            {"id": "bruno", "preferredName": "Bruno"},
            {"id": "carla", "preferredName": "Carla"},
            {"id": "dora", "preferredName": "Dora"},
            {"id": "fic_exemplo", "preferredName": "Fictício", "fictional": True},
        ],
        "relations": relations,
        "negative_pairs": [
            {"subject": "carla", "object": "dora", "chapters": ["1"], "expected": "sem_relacao"},
            {"subject": "bruno", "object": "dora", "chapters": ["2"], "expected": "sem_relacao"},
        ],
    }


def rev(canon: IngestResult, quote: str, *, start: int | None = None) -> dict[str, Any]:
    """Evidência da execução sobre `quote` (início opcional dentro do trecho)."""
    s, e = span(canon, quote)
    return {"quote": quote, "startOffset": s if start is None else start, "endOffset": e}


def rclaim(subject: str, type_: str, object_: str, cls: str = "afirmada", **kw: Any) -> dict:
    return {"subject": subject, "type": type_, "object": object_, "class": cls, **kw}


def make_run(canon: IngestResult) -> dict[str, Any]:
    """Quinze claims; ver o mapa claim → resultado em tests/test_eval.py."""
    bad = {"quote": "texto que não existe", "startOffset": 0, "endOffset": 20}
    claims = [
        # c1: inverso do G1 → acerto exato; prova alta
        rclaim("Bruno", "vigiado_por", "Ana", evidence=[rev(canon, Q_VIGIA)]),
        # c2: G2 com a atribuição errada (ana, não bruno); nível próprio N3
        rclaim("Carla", "exerce_coercao_sobre", "Ana", "alegada", asserted_by="Ana", level="N3",
               evidence=[rev(canon, "Carla disse que a chave velha")]),
        # c3: G3 com sujeito e objeto trocados (simétrica), por alias, classe errada;
        #     a evidência está noutro lugar (cap. 2) → relação certa, prova sem coincidência
        rclaim("Carla", "amizade_com", "a vizinha", "inferida", evidence=[rev(canon, Q_BRUNO)]),
        # c4: tipo irmão do G4 (mesmo pai relacao_de_mediacao) → acerto no pai
        rclaim("Bruno", "age_em_nome_de", "Carla", evidence=[rev(canon, Q_BRUNO)]),
        # c5: casa só com G6 (sem prova) → ignorada
        rclaim("Carla", "adversario_de", "Bruno", evidence=[rev(canon, Q_BOLSO)]),
        # c6: pessoa sem alinhamento; evidência não localizada → falso positivo
        rclaim("Ana", "amizade_com", "Fulano", evidence=[bad]),
        # c7: duplicata de c1 → fundida
        rclaim("Ana", "exerce_vigilancia_sobre", "Bruno", evidence=[rev(canon, Q_VIGIA)]),
        # c8: evidência só no cap. 3 → fora do escopo
        rclaim("Ana", "amizade_com", "Bruno", evidence=[rev(canon, Q_FULANO)]),
        # c9: texto encaixado que acerta G5
        rclaim("Ana", "vinculo_amoroso_com", "Bruno", narrative_scope="texto_encaixado",
               evidence=[rev(canon, Q_CARLA)]),
        # c10: o mesmo par, marcado `obra` → falso positivo (ADR 011)
        rclaim("Ana", "vinculo_amoroso_com", "Bruno", evidence=[rev(canon, Q_CARLA)]),
        # c11: disjunta de c10 (mesmo par) → alerta
        rclaim("Ana", "parente_de", "Bruno", evidence=[rev(canon, Q_CARLA)]),
        # c12: viola o par de controle carla × dora (cap. 1)
        rclaim("Carla", "interesse_amoroso_por", "Dora", evidence=[rev(canon, Q_BOLSO)]),
        # c13 e c14: tipo inexistente e tipo abstrato → tipo inválido, falso positivo
        rclaim("Ana", "tipo_inexistente", "Bruno"),
        rclaim("Ana", "relacao_de_poder", "Bruno"),
        # c15: G7 com as duas evidências → acerto; prova em conjunto
        rclaim("Ana", "adversario_de", "Bruno",
               evidence=[rev(canon, Q_VIGIA), rev(canon, Q_BRUNO)]),
    ]  # fmt: skip
    return {
        "schema_version": 1,
        "run_id": "sintetica-01",
        "meta": {
            "model": "modelo-falso",
            "prompt_version": "p0",
            "parameters": {"temperature": 0.0},
            "level": "N1",
            "lens": "padrao",
        },
        "entities": [
            {"name": "Ana", "aliases": ["a vizinha"]},
            {"name": "Bruno"},
            {"name": "Carla"},
            {"name": "Fulano"},
        ],
        "claims": claims,
        "calls": [{"json_valid": True}, {"json_valid": True}, {"json_valid": True},
                  {"json_valid": False}],
    }  # fmt: skip

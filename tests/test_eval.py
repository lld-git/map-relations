"""`eval` (B02 §7): métricas esperadas calculadas à mão sobre o cenário sintético.

Mapa claim → resultado (ver tests/eval_helpers.py):
  c1 acerto exato (inverso)      c2 relaxada acerta, estrita erra (asserted_by)
  c3 acerto exato (simétrica)    c4 acerto só no tipo pai
  c5 ignorada (gabarito sem prova)   c6 pessoa sem alinhamento
  c7 duplicata de c1             c8 fora do escopo (cap. 3)
  c9 texto encaixado que acerta  c10 `obra` sobre item encaixado (FP)
  c11 disjunta de c10            c12 viola o par de controle
  c13/c14 tipo inválido          c15 acerto exato, prova em conjunto
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from map_relations.evaluation.eval_cli import cmd_eval
from map_relations.evaluation.evaluate import evaluate
from map_relations.evaluation.gold import GoldFile
from map_relations.evaluation.matching import EvalInputError, normalize_name
from map_relations.evaluation.report import flat_metrics, render_markdown
from map_relations.evaluation.run_file import RunFile
from tests.eval_helpers import (
    ONTOLOGY,
    Q_BRUNO,
    Q_CARLA,
    Q_VIGIA,
    _rel,
    gev,
    make_canon,
    make_gold,
    make_run,
    rclaim,
    rev,
)
from tests.gold_helpers import write_processed

CANON = make_canon()


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return evaluate(
        RunFile.model_validate(make_run(CANON)),
        GoldFile.model_validate(make_gold(CANON)),
        ONTOLOGY,
        CANON,
    )


def _gold_ids() -> dict[str, str]:
    """Id da relação do gabarito por 'sujeito|tipo'."""
    rels = make_gold(CANON)["relations"]
    return {f"{r['subject']}|{r['type']}": r["id"] for r in rels if not r.get("fictional")}


def approx(x: float) -> Any:
    return pytest.approx(x)


# ── escopo e contagens ────────────────────────────────────────────────────────


def test_scope_and_counts(report):
    ex = report["execucao"]
    assert ex["claims_total"] == 15
    assert ex["fora_do_escopo"] == 1  # c8
    assert ex["duplicadas"] == 1  # c7
    assert ex["tipo_invalido"] == 2  # c13, c14
    assert ex["avaliadas_obra"] == 12
    assert ex["texto_encaixado"] == 1  # c9
    g = report["gabarito"]
    assert g["relacoes_positivas"] == 5  # G1–G4, G7 (provadas, `obra`)
    assert g["relacoes_sem_prova_ignoradas"] == 1  # G6
    assert g["ficticias_ignoradas"] == 1
    assert g["pares_de_controle"] == 2


def test_unproved_gold_is_neither_hit_nor_false_positive(report):
    for measure in ("estrita", "relaxada"):
        assert report["medidas"][measure]["exato"]["ignoradas_sem_prova"] == 1  # c5
    # FP estrito = 8, não 9: c5 não conta
    assert report["medidas"]["estrita"]["exato"]["por_tipo"]["micro"]["fp"] == 8


# ── estrita × relaxada ────────────────────────────────────────────────────────


def test_strict_micro(report):
    micro = report["medidas"]["estrita"]["exato"]["por_tipo"]["micro"]
    assert (micro["tp"], micro["fp"], micro["fn"]) == (3, 8, 2)
    assert micro["p"] == approx(3 / 11)
    assert micro["r"] == approx(3 / 5)
    assert micro["f1"] == approx(6 / 16)


def test_relaxed_finds_what_strict_misses_by_asserted_by(report):
    micro = report["medidas"]["relaxada"]["exato"]["por_tipo"]["micro"]
    assert (micro["tp"], micro["fp"], micro["fn"]) == (4, 7, 1)  # c2 só na relaxada
    assert micro["f1"] == approx(8 / 16)
    strict_types = report["medidas"]["estrita"]["exato"]["por_tipo"]["por_grupo"]
    relaxed_types = report["medidas"]["relaxada"]["exato"]["por_tipo"]["por_grupo"]
    assert strict_types["exerce_coercao_sobre"]["tp"] == 0
    assert relaxed_types["exerce_coercao_sobre"]["tp"] == 1


def test_by_type_and_macro(report):
    s = report["medidas"]["estrita"]["exato"]["por_tipo"]
    am = s["por_grupo"]["amizade_com"]  # c3 acerta, c6 é falso positivo
    assert (am["tp"], am["fp"], am["fn"]) == (1, 1, 0)
    assert am["p"] == approx(0.5) and am["r"] == approx(1.0) and am["f1"] == approx(2 / 3)
    assert s["por_grupo"]["representa_juridicamente"]["fn"] == 1  # G4 só no pai
    assert s["por_grupo"]["(tipo_invalido)"]["fp"] == 2
    # 10 tipos; F1 não nulo: vigilância 1, amizade 2/3, adversário 1
    assert s["macro_f1"] == approx((1 + 2 / 3 + 1) / 10)
    r = report["medidas"]["relaxada"]["exato"]["por_tipo"]
    assert r["macro_f1"] == approx((1 + 1 + 2 / 3 + 1) / 10)


def test_family_parent_hit(report):
    fs = report["medidas"]["estrita"]["familia"]
    fr = report["medidas"]["relaxada"]["familia"]
    assert fs["acertos_no_pai"] == fr["acertos_no_pai"] == 1  # c4 × G4
    assert (fs["micro"]["tp"], fs["micro"]["fp"], fs["micro"]["fn"]) == (4, 7, 1)
    assert fs["micro"]["f1"] == approx(8 / 16)
    assert (fr["micro"]["tp"], fr["micro"]["fp"], fr["micro"]["fn"]) == (5, 6, 0)
    assert fr["micro"]["f1"] == approx(10 / 16)
    med = fs["por_grupo"]["relacao_de_mediacao"]
    assert (med["tp"], med["fp"], med["fn"]) == (1, 0, 0)
    assert fs["por_grupo"]["(sem_pai)"]["fp"] == 2  # tipos inválidos


# ── atribuição e classe ───────────────────────────────────────────────────────


def test_attribution_line(report):
    a = report["atribuicao"]
    ids = _gold_ids()
    assert a["acertos_relaxados"] == 4
    assert a["classe_certa"] == approx(3 / 4)  # c3 é `inferida` no gabarito `afirmada`
    assert a["alegadas_no_gabarito"] == 1
    assert a["asserted_by_certo"] == approx(0.0)  # c2: ana em vez de bruno
    assert a["atribuicao_correta"] == approx(2 / 4)
    assert {w["relacao"] for w in a["erradas"]} == {
        ids["carla|exerce_coercao_sobre"],
        ids["ana|amizade_com"],
    }
    wrong_ab = next(w for w in a["erradas"] if w["gabarito"]["classe"] == "alegada")
    assert wrong_ab["gabarito"]["asserted_by"] == "bruno"
    assert wrong_ab["execucao"]["asserted_by"] == "ana"


def test_class_confusion_matrix(report):
    assert report["atribuicao"]["matriz_classe"] == {
        "afirmada": {"afirmada": 2, "inferida": 1},
        "alegada": {"alegada": 1},
    }


# ── nível e lente ─────────────────────────────────────────────────────────────


def test_by_level_and_lens(report):
    niv = report["medidas"]["relaxada"]["nivel"]
    assert (niv["N1"]["tp"], niv["N1"]["fp"], niv["N1"]["fn"]) == (3, 7, 2)
    assert niv["N1"]["f1"] == approx(6 / 15)
    assert (niv["N3"]["tp"], niv["N3"]["fp"], niv["N3"]["fn"]) == (1, 0, 4)  # c2 tem nível próprio
    assert niv["N3"]["f1"] == approx(2 / 6)
    assert report["medidas"]["estrita"]["nivel"]["N3"]["f1"] == approx(0.0)
    lente = report["medidas"]["estrita"]["lente"]
    assert list(lente) == ["padrao"] and lente["padrao"]["f1"] == approx(6 / 16)


# ── provas ────────────────────────────────────────────────────────────────────


def test_proof_is_measured_apart_from_the_relation(report):
    s = report["medidas"]["estrita"]["prova"]
    # acertos estritos: c1 (evidência alta), c3 (relação certa, evidência noutro
    # lugar), c15 (conjunto)
    assert (s["acertos"], s["evidencia_alta"], s["conjunto"], s["nenhuma"]) == (3, 1, 1, 1)
    assert s["parcial"] == 0 and s["taxa"] == approx(2 / 3)
    r = report["medidas"]["relaxada"]["prova"]
    assert (r["acertos"], r["evidencia_alta"], r["conjunto"], r["nenhuma"]) == (4, 2, 1, 1)
    assert r["taxa"] == approx(3 / 4)


def test_located_evidence_rate(report):
    p = report["provas"]
    assert (p["evidencias_total"], p["evidencias_localizadas"]) == (14, 13)  # c6 não localiza
    assert p["localizadas"] == approx(13 / 14)


def test_json_valid_rate(report):
    j = report["json_valido"]
    assert (j["chamadas"], j["validas"]) == (4, 3)
    assert j["taxa"] == approx(0.75)


# ── pessoas, controle, encaixado, alertas ─────────────────────────────────────


def test_persons(report):
    p = report["pessoas"]
    assert (p["gabarito"], p["alinhadas"]) == (4, 3)  # a fictícia fica de fora
    assert p["recall"] == approx(0.75)
    assert p["gabarito_sem_alinhamento"] == ["dora"]
    assert p["execucao_sem_alinhamento"] == ["Fulano"]


def test_control_pairs(report):
    c = report["controle"]
    assert (c["pares"], c["violacoes"]) == (2, 1)
    assert c["taxa"] == approx(0.5)
    assert c["lista"][0]["par"] == ["carla", "dora"]
    assert [x["tipo"] for x in c["lista"][0]["claims"]] == ["interesse_amoroso_por"]
    # o par bruno × dora vale só no cap. 2: nenhuma claim lá


def test_embedded_text_apart_and_wrong_scope_is_false_positive(report):
    t = report["texto_encaixado"]
    assert (t["gabarito"], t["execucao"]) == (1, 1)
    assert (t["acertos_estrita"], t["acertos_relaxada"]) == (1, 1)
    assert t["obra_sobre_item_encaixado"] == 1  # c10, ADR 011
    # c9 e G5 estão fora das métricas principais
    assert report["medidas"]["estrita"]["exato"]["por_tipo"]["por_grupo"][
        "vinculo_amoroso_com"
    ] == {"tp": 0, "fp": 1, "fn": 0, "p": 0.0, "r": None, "f1": 0.0}


def test_disjoint_alert_only_for_main_scope(report):
    assert len(report["alertas"]) == 1
    assert "claim#10" in report["alertas"][0] and "claim#11" in report["alertas"][0]


# ── regras de casamento (casos mínimos) ───────────────────────────────────────


def _mini(relations: list[dict], claims: list[dict], **gold_over) -> dict[str, Any]:
    gold = make_gold(CANON)
    gold["relations"] = relations
    gold["negative_pairs"] = []
    gold.update(gold_over)
    run = make_run(CANON)
    run["claims"] = claims
    return evaluate(
        RunFile.model_validate(run), GoldFile.model_validate(gold), ONTOLOGY, CANON
    )


def _micro(rep, measure="estrita", key="exato"):
    block = rep["medidas"][measure][key]
    return block["por_tipo"]["micro"] if key == "exato" else block["micro"]


def test_each_gold_item_is_used_at_most_once():
    g = _rel(CANON, subject="carla", type="exerce_coercao_sobre", object="ana",
             **{"class": "alegada"}, asserted_by="bruno",
             evidence=[gev(CANON, Q_CARLA, "1")])  # fmt: skip
    claims = [  # a primeira atribui errado, a segunda certo; só um item do gabarito
        rclaim("Carla", "exerce_coercao_sobre", "Ana", "alegada", asserted_by="Ana"),
        rclaim("Carla", "exerce_coercao_sobre", "Ana", "alegada", asserted_by="Bruno"),
    ]
    rep = _mini([g], claims)
    assert (_micro(rep)["tp"], _micro(rep)["fp"]) == (1, 1)
    rel = _micro(rep, "relaxada")
    assert (rel["tp"], rel["fp"]) == (1, 1)
    assert rep["atribuicao"]["asserted_by_certo"] == approx(1.0)  # casou com a certa primeiro


def _parent_case(gold_type, gold_s, gold_o, run_type, run_s, run_o, run_ab=None, gold_ab=None):
    cls = {"class": "alegada"} if gold_ab else {}
    g = _rel(CANON, subject=gold_s, type=gold_type, object=gold_o, asserted_by=gold_ab,
             evidence=[gev(CANON, Q_VIGIA, "1")], **cls)  # fmt: skip
    kw = {"asserted_by": run_ab} if run_ab else {}
    run_cls = "alegada" if run_ab else "afirmada"
    return _mini([g], [rclaim(run_s, run_type, run_o, run_cls, **kw)])


def test_parent_hit_requires_direction_between_asymmetric_types():
    ok = _parent_case("representa_juridicamente", "bruno", "carla",
                      "age_em_nome_de", "Bruno", "Carla")  # fmt: skip
    assert ok["medidas"]["relaxada"]["familia"]["acertos_no_pai"] == 1
    reversed_ = _parent_case("representa_juridicamente", "bruno", "carla",
                             "age_em_nome_de", "Carla", "Bruno")  # fmt: skip
    assert reversed_["medidas"]["relaxada"]["familia"]["acertos_no_pai"] == 0


def test_parent_hit_ignores_direction_when_a_type_is_symmetric():
    rep = _parent_case("parente_de", "ana", "bruno", "progenitor_de", "Bruno", "Ana")
    assert rep["medidas"]["relaxada"]["familia"]["acertos_no_pai"] == 1


def test_parent_hit_strict_needs_same_asserted_by_relaxed_does_not():
    rep = _parent_case("representa_juridicamente", "bruno", "carla",
                       "age_em_nome_de", "Bruno", "Carla", run_ab="Ana")  # fmt: skip
    # execução alegada (asserted_by ana) × gabarito afirmada: asserted_by diferente
    assert rep["medidas"]["estrita"]["familia"]["acertos_no_pai"] == 0
    assert rep["medidas"]["relaxada"]["familia"]["acertos_no_pai"] == 1


def test_exact_hit_takes_precedence_over_parent_hit():
    g = _rel(CANON, subject="bruno", type="representa_juridicamente", object="carla",
             evidence=[gev(CANON, Q_BRUNO, "2")])  # fmt: skip
    rep = _mini([g], [
        rclaim("Bruno", "age_em_nome_de", "Carla"),
        rclaim("Bruno", "representa_juridicamente", "Carla"),
    ])  # fmt: skip
    assert _micro(rep)["tp"] == 1
    assert rep["medidas"]["estrita"]["familia"]["acertos_no_pai"] == 0  # o item já foi usado


def test_contradicting_evidence_does_not_prove_the_relation():
    rel = _rel(CANON, subject="ana", type="exerce_vigilancia_sobre", object="bruno",
               evidence=[{**gev(CANON, Q_VIGIA, "1"), "polarity": "contradiz"}])  # fmt: skip
    rep = _mini([rel], [rclaim("Ana", "exerce_vigilancia_sobre", "Bruno")])
    assert rep["gabarito"]["relacoes_positivas"] == 0
    assert rep["gabarito"]["relacoes_sem_prova_ignoradas"] == 1
    assert _micro(rep)["fp"] == 0  # a claim casa com item sem prova: ignorada


def test_run_evidence_over_contradicting_gold_evidence_is_not_proof():
    rel = _rel(CANON, subject="ana", type="exerce_vigilancia_sobre", object="bruno",
               evidence=[gev(CANON, Q_VIGIA, "1"),
                         {**gev(CANON, Q_BRUNO, "2"), "polarity": "contradiz"}])  # fmt: skip
    rep = _mini([rel], [rclaim("Ana", "exerce_vigilancia_sobre", "Bruno",
                               evidence=[rev(CANON, Q_BRUNO)])])  # fmt: skip
    assert rep["medidas"]["estrita"]["prova"]["nenhuma"] == 1


def test_conjoint_needs_every_supporting_evidence_covered():
    rel = _rel(CANON, subject="ana", type="adversario_de", object="bruno",
               provas_em_conjunto="suficiente",
               evidence=[gev(CANON, Q_VIGIA, "1", "medio"),
                         gev(CANON, Q_BRUNO, "2", "medio")])  # fmt: skip
    one = _mini([rel], [rclaim("Ana", "adversario_de", "Bruno", evidence=[rev(CANON, Q_VIGIA)])])
    assert one["medidas"]["estrita"]["prova"]["parcial"] == 1
    both = _mini([rel], [rclaim("Ana", "adversario_de", "Bruno",
                                evidence=[rev(CANON, Q_VIGIA), rev(CANON, Q_BRUNO)])])  # fmt: skip
    assert both["medidas"]["estrita"]["prova"]["conjunto"] == 1


def test_run_alias_in_two_gold_entities_is_a_gold_error():
    gold = make_gold(CANON)
    gold["entities"][1]["aliases"] = ["a vizinha"]  # bruno e ana com o mesmo alias
    with pytest.raises(EvalInputError, match="a vizinha"):
        evaluate(RunFile.model_validate(make_run(CANON)), GoldFile.model_validate(gold),
                 ONTOLOGY, CANON)  # fmt: skip


def test_names_are_normalized_without_accents_case_or_spaces():
    assert normalize_name("  JOSÉ   Árvore ") == normalize_name("jose arvore")


# ── relatório e métricas planas ───────────────────────────────────────────────


def test_flat_metrics_have_stable_names(report):
    m = flat_metrics(report)
    assert m["p.estrita.micro"] == approx(3 / 11)
    assert m["f1.relaxada.micro"] == approx(0.5)
    assert m["p.estrita.amizade_com"] == approx(0.5)
    assert m["f1.familia.relaxada.relacao_de_poder"] is not None
    assert m["atribuicao.asserted_by"] == approx(0.0)
    assert m["atribuicao.classe"] == approx(0.75)
    assert m["controle.violacoes"] == 1.0
    assert m["pessoas.recall"] == approx(0.75)
    assert m["json_valido.taxa"] == approx(0.75)
    assert m["prova.estrita.taxa"] == approx(2 / 3)
    assert m["nivel.N3.f1.relaxada"] == approx(2 / 6)
    assert all(isinstance(v, float) for v in m.values())


def test_markdown_covers_every_group(report):
    md = render_markdown(report)
    for heading in ("Medida estrita", "Medida relaxada", "Por família", "Por nível", "Por lente",
                    "Atribuição", "Matriz de classe", "Pares de controle", "Texto encaixado",
                    "Alertas", "Evidências localizadas", "JSON válido", "Pessoas"):
        assert heading in md, heading


# ── CLI ───────────────────────────────────────────────────────────────────────


def _write(tmp_path: Path, run: dict | None = None, gold: dict | None = None) -> tuple:
    proc = write_processed(tmp_path / "w", CANON)
    run_p, gold_p = tmp_path / "run.json", tmp_path / "gold.json"
    run_p.write_text(json.dumps(run or make_run(CANON)), encoding="utf-8")
    gold_p.write_text(json.dumps(gold or make_gold(CANON)), encoding="utf-8")
    return run_p, gold_p, proc


def test_cli_writes_report_and_exits_zero(tmp_path, capsys):
    run_p, gold_p, proc = _write(tmp_path)
    out = tmp_path / "reports"
    code = cmd_eval(run_p, gold_p, proc, out, tmp_path / "x", track=False)
    assert code == 0
    assert (out / "sintetica-01" / "report.md").is_file()
    data = json.loads((out / "sintetica-01" / "report.json").read_text(encoding="utf-8"))
    assert data["run_id"] == "sintetica-01"


def test_cli_exit_2_when_gold_hash_differs(tmp_path, capsys):
    gold = make_gold(CANON)
    gold["source"]["content_hash"] = "sha256:" + "0" * 64
    run_p, gold_p, proc = _write(tmp_path, gold=gold)
    assert cmd_eval(run_p, gold_p, proc, tmp_path / "r", tmp_path / "x", track=False) == 2
    assert "fill-offsets" in capsys.readouterr().err
    assert not (tmp_path / "r").exists()


def test_cli_exit_2_on_invalid_run(tmp_path, capsys):
    run = make_run(CANON)
    run["claims"][1].pop("asserted_by")  # alegada sem asserted_by
    run_p, gold_p, proc = _write(tmp_path, run=run)
    assert cmd_eval(run_p, gold_p, proc, tmp_path / "r", tmp_path / "x", track=False) == 2


def test_cli_rejects_run_id_that_escapes_the_reports_folder(tmp_path):
    run = copy.deepcopy(make_run(CANON))
    run["run_id"] = "../fora"
    run_p, gold_p, proc = _write(tmp_path, run=run)
    assert cmd_eval(run_p, gold_p, proc, tmp_path / "r", tmp_path / "x", track=False) == 2


def test_run_schema_is_generated_and_up_to_date():
    from scripts.generate_schemas import EXTRA_SCHEMAS, SCHEMAS_DIR, render

    model = EXTRA_SCHEMAS["run.schema.json"]
    assert (SCHEMAS_DIR / "run.schema.json").read_text(encoding="utf-8") == render(model)

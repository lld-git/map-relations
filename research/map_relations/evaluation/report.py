"""Relatório do `eval`: métricas planas para o MLflow e Markdown legível (B02 §7, §8).

Nomes estáveis das métricas (só números; nada da obra):
`p|r|f1.<medida>.<tipo>`, `p|r|f1.<medida>.micro`, `f1.<medida>.macro`,
`p|r|f1.familia.<medida>.<pai>`, `atribuicao.*`, `prova.<medida>.*`,
`nivel.<n>.f1.<medida>`, `lente.<l>.f1.<medida>`, `controle.*`, `pessoas.recall`…
Valores ausentes (divisão por zero) não são registrados.
"""

from __future__ import annotations

import re
from typing import Any

from map_relations.evaluation.matching import MEASURES

Report = dict[str, Any]


def _name(part: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.\-]", "_", part).strip("_")


def flat_metrics(report: Report) -> dict[str, float]:
    out: dict[str, float] = {}

    def put(key: str, value: Any) -> None:
        if isinstance(value, bool):
            value = int(value)
        if isinstance(value, int | float):
            out[key] = float(value)

    for measure in MEASURES:
        m = report["medidas"][measure]
        tipo = m["exato"]["por_tipo"]
        for t, prf in tipo["por_grupo"].items():
            for k in ("p", "r", "f1"):
                put(f"{k}.{measure}.{_name(t)}", prf[k])
        for k in ("p", "r", "f1"):
            put(f"{k}.{measure}.micro", tipo["micro"][k])
        put(f"f1.{measure}.macro", tipo["macro_f1"])
        fam = m["familia"]
        for parent, prf in fam["por_grupo"].items():
            for k in ("p", "r", "f1"):
                put(f"{k}.familia.{measure}.{_name(parent)}", prf[k])
        for k in ("p", "r", "f1"):
            put(f"{k}.familia.{measure}.micro", fam["micro"][k])
        put(f"f1.familia.{measure}.macro", fam["macro_f1"])
        put(f"acertos.{measure}.tipo_pai", fam["acertos_no_pai"])
        for attr in ("nivel", "lente"):
            for group, prf in m[attr].items():
                put(f"{attr}.{_name(group)}.f1.{measure}", prf["f1"])
        pr = m["prova"]
        put(f"prova.{measure}.taxa", pr["taxa"])
        for k in ("evidencia_alta", "conjunto", "parcial", "nenhuma"):
            put(f"prova.{measure}.{k}", pr[k])
    a = report["atribuicao"]
    put("atribuicao.classe", a["classe_certa"])
    put("atribuicao.asserted_by", a["asserted_by_certo"])
    put("atribuicao.correta", a["atribuicao_correta"])
    put("prova.evidencias_localizadas", report["provas"]["localizadas"])
    put("json_valido.taxa", report["json_valido"]["taxa"])
    put("pessoas.recall", report["pessoas"]["recall"])
    put("controle.violacoes", report["controle"]["violacoes"])
    put("controle.taxa", report["controle"]["taxa"])
    for k in ("gabarito", "execucao", "acertos_estrita", "acertos_relaxada"):
        put(f"encaixado.{k}", report["texto_encaixado"][k])
    put(
        "encaixado.obra_sobre_item_encaixado",
        report["texto_encaixado"]["obra_sobre_item_encaixado"],
    )
    put("alertas.disjuncoes", len(report["alertas"]))
    for k, v in report["execucao"].items():
        put(f"execucao.{k}", v)
    return out


def _f(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}"


def _prf_row(label: str, prf: dict[str, Any]) -> str:
    return (
        f"| {label} | {prf['tp']} | {prf['fp']} | {prf['fn']} | "
        f"{_f(prf['p'])} | {_f(prf['r'])} | {_f(prf['f1'])} |"
    )


_HEAD = "| | TP | FP | FN | P | R | F1 |\n|---|--:|--:|--:|--:|--:|--:|"


def render_markdown(report: Report) -> str:
    meta = report["meta"]
    ex = report["execucao"]
    g = report["gabarito"]
    lines = [
        f"# Avaliação — {report['run_id']}",
        "",
        f"Modelo `{meta['model']}`, prompt `{meta['prompt_version']}`, nível "
        f"`{meta['level']}`, lente `{meta['lens']}`, ontologia v{report['ontology_version']}.",
        "",
        "> Este relatório pode citar a obra (ids e nomes); fica em `eval/reports/`, fora do Git.",
        "",
        "## Escopo",
        "",
        f"- Gabarito: {g['relacoes_positivas']} relações provadas no escopo `obra`; "
        f"{g['relacoes_sem_prova_ignoradas']} sem prova (ignoradas); "
        f"{g['pares_de_controle']} pares de controle.",
        f"- Execução: {ex['claims_total']} claims; {ex['fora_do_escopo']} fora do escopo; "
        f"{ex['duplicadas']} duplicadas fundidas; {ex['tipo_invalido']} com tipo inválido; "
        f"{ex['avaliadas_obra']} avaliadas (`obra`); {ex['texto_encaixado']} em texto encaixado.",
    ]
    for measure in MEASURES:
        m = report["medidas"][measure]
        t = m["exato"]["por_tipo"]
        lines += ["", f"## Medida {measure} — por tipo (acerto exato)", "", _HEAD]
        lines += [_prf_row(k, v) for k, v in t["por_grupo"].items()]
        lines += [
            _prf_row("**micro**", t["micro"]),
            f"| **macro F1** | | | | | | {_f(t['macro_f1'])} |",
        ]
        fam = m["familia"]
        lines += [
            "",
            f"### Por família (acerto no tipo pai; {fam['acertos_no_pai']} acertos só no pai)",
            "",
            _HEAD,
        ]
        lines += [_prf_row(k, v) for k, v in fam["por_grupo"].items()]
        lines += [
            _prf_row("**micro**", fam["micro"]),
            f"| **macro F1** | | | | | | {_f(fam['macro_f1'])} |",
        ]
        for attr, title in (("nivel", "Por nível"), ("lente", "Por lente")):
            lines += ["", f"### {title}", "", _HEAD]
            lines += [_prf_row(k, v) for k, v in m[attr].items()]
        p = m["prova"]
        lines += [
            "",
            "### Prova (medida à parte da relação)",
            "",
            f"{p['acertos']} acertos: {p['evidencia_alta']} por evidência alta, "
            f"{p['conjunto']} por conjunto, {p['parcial']} parciais, "
            f"{p['nenhuma']} sem coincidência → taxa {_f(p['taxa'])}.",
        ]
    a = report["atribuicao"]
    lines += [
        "",
        "## Atribuição (nos acertos relaxados)",
        "",
        f"- Acertos relaxados: {a['acertos_relaxados']}; classe certa {_f(a['classe_certa'])}; "
        f"alegadas {a['alegadas_no_gabarito']} com `asserted_by` certo "
        f"{_f(a['asserted_by_certo'])}; atribuição correta {_f(a['atribuicao_correta'])}.",
    ]
    if a["matriz_classe"]:
        lines += ["", "Matriz de classe (linha = gabarito, coluna = execução):", ""]
        cols = sorted({c for row in a["matriz_classe"].values() for c in row})
        lines += ["| | " + " | ".join(cols) + " |", "|---|" + "--:|" * len(cols)]
        for gc, row in sorted(a["matriz_classe"].items()):
            lines.append(f"| {gc} | " + " | ".join(str(row.get(c, 0)) for c in cols) + " |")
    if a["erradas"]:
        lines += ["", "Atribuições erradas:", ""]
        for w in a["erradas"]:
            lines.append(
                f"- {w['relacao']}: gabarito {w['gabarito']['classe']}/"
                f"{w['gabarito']['asserted_by']} × execução {w['execucao']['classe']}/"
                f"{w['execucao']['asserted_by']}"
            )
    pr, js, pe, ct, te = (
        report["provas"], report["json_valido"], report["pessoas"],
        report["controle"], report["texto_encaixado"],
    )  # fmt: skip
    lines += [
        "",
        "## Provas, JSON e pessoas",
        "",
        f"- Evidências localizadas (`canonical[start:end] == quote`): "
        f"{pr['evidencias_localizadas']}/{pr['evidencias_total']} ({_f(pr['localizadas'])}).",
        f"- JSON válido: {js['validas']}/{js['chamadas']} ({_f(js['taxa'])}).",
        f"- Pessoas: recall {_f(pe['recall'])} ({pe['alinhadas']}/{pe['gabarito']}). "
        f"Sem alinhamento no gabarito: {pe['gabarito_sem_alinhamento'] or 'nenhuma'}; "
        f"na execução: {pe['execucao_sem_alinhamento'] or 'nenhuma'}.",
        "",
        "## Pares de controle",
        "",
        f"- {ct['violacoes']} violação(ões) em {ct['pares']} par(es) (taxa {_f(ct['taxa'])}).",
    ]
    for v in ct["lista"]:
        tipos = ", ".join(f"{c['tipo']} (cap. {','.join(c['capitulos'])})" for c in v["claims"])
        lines.append(f"  - {v['par'][0]} × {v['par'][1]}: {tipos}")
    lines += [
        "",
        "## Texto encaixado (à parte)",
        "",
        f"- Gabarito {te['gabarito']}, execução {te['execucao']}; acertos estrita "
        f"{te['acertos_estrita']}, relaxada {te['acertos_relaxada']}; claims `obra` que casam "
        f"com item encaixado (falso positivo, ADR 011): {te['obra_sobre_item_encaixado']}.",
        "",
        "## Alertas",
        "",
    ]
    lines += [f"- {x}" for x in report["alertas"]] or ["- nenhum"]
    return "\n".join(lines) + "\n"

"""Avaliação de uma execução contra o gabarito (B02 §7).

`evaluate` devolve um relatório em dicionário (pronto para JSON). Ele só traz
ids, tipos, classes, contagens e referências "cap. X, § Y": nenhuma citação.
Os itens `fictional` do gabarito são exemplos e ficam de fora.

Decisões de leitura (registradas no ADR 012/013):
- só relações **provadas** do gabarito (`relation_proof`) são positivos;
  as sem prova são contadas e ignoradas (nem acerto, nem falso positivo);
- claims duplicadas (mesma chave estrita) viram uma, com as evidências somadas;
- escopo: claim sem nenhuma evidência localizada num capítulo do gabarito, e
  com ao menos uma localizada fora deles, é "fora do escopo"; sem evidência
  localizada nenhuma, fica no escopo (conta contra a precisão: nunca chute);
- as métricas principais são só do escopo `obra`; `texto_encaixado` sai à parte.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable
from typing import Any

from map_relations.core.models import Claim, ClaimClass, NarrativeScope, RelationType
from map_relations.core.ontology import Ontology
from map_relations.evaluation.gold import (
    Canonical,
    GoldFile,
    Polarity,
    Support,
    relation_proof,
)
from map_relations.evaluation.matching import (
    INVALID_TYPE,
    MEASURES,
    UNALIGNED,
    EvalInputError,
    Item,
    MatchResult,
    make_item,
    match,
    normalize_name,
    parent_of,
)
from map_relations.evaluation.run_file import RunFile

Report = dict[str, Any]


def _prf(tp: int, fp: int, fn: int) -> dict[str, Any]:
    """P e R indefinidos (None) sem denominador; F1 = 2·TP / (2·TP + FP + FN)."""
    p = tp / (tp + fp) if tp + fp else None
    r = tp / (tp + fn) if tp + fn else None
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"tp": tp, "fp": fp, "fn": fn, "p": p, "r": r, "f1": f1}


def _pct(num: int, den: int) -> float | None:
    return num / den if den else None


def _label(item: Item) -> str:
    return item.type_id if item.valid_type else INVALID_TYPE


# ── alinhamento de pessoas ────────────────────────────────────────────────────


def _gold_name_index(gold: GoldFile) -> dict[str, set[str]]:
    index: dict[str, set[str]] = defaultdict(set)
    for ent in gold.entities:
        if ent.fictional:
            continue
        for name in (ent.preferred_name, *ent.aliases):
            index[normalize_name(name)].add(ent.id)
    ambiguous = sorted(n for n, ids in index.items() if len(ids) > 1)
    if ambiguous:
        raise EvalInputError(
            [f"gabarito: o nome/alias '{n}' casa com mais de uma entidade" for n in ambiguous]
        )
    return index


class _Aligner:
    def __init__(self, gold: GoldFile, run: RunFile) -> None:
        self.index = _gold_name_index(gold)
        self.names: dict[str, str] = {}  # nome normalizado da execução → id do gabarito
        self.aligned: set[str] = set()
        self.unaligned_run: list[str] = []
        for ent in run.entities:
            ids: set[str] = set()
            for name in (ent.name, *ent.aliases):
                ids |= self.index.get(normalize_name(name), set())
            if len(ids) == 1:
                gid = next(iter(ids))
                self.aligned.add(gid)
                for name in (ent.name, *ent.aliases):
                    self.names[normalize_name(name)] = gid
            else:
                note = " (ambígua)" if ids else ""
                self.unaligned_run.append(ent.name + note)

    def resolve(self, name: str) -> str:
        key = normalize_name(name)
        if key in self.names:
            return self.names[key]
        ids = self.index.get(key, set())
        return next(iter(ids)) if len(ids) == 1 else UNALIGNED + key


# ── montagem dos itens ────────────────────────────────────────────────────────


def _gold_items(
    gold: GoldFile, ontology: Ontology, types: dict[str, RelationType]
) -> tuple[list[Item], list[Item], int]:
    """(positivos provados, sem prova, nº de fictícios ignorados)."""
    items: list[Item] = []
    unproved: list[Item] = []
    fictional = 0
    for rel in gold.relations:
        if rel.fictional:
            fictional += 1
            continue
        proof = relation_proof(rel)
        it = make_item(
            rel.id, rel.type_, rel.subject, rel.object_, rel.class_,
            rel.asserted_by, rel.narrative_scope, ontology, types,
        )  # fmt: skip
        it.relation, it.proof = rel, proof
        (items if proof.proved else unproved).append(it)
    return items, unproved, fictional


def _located(ev_start: int, ev_end: int, quote: str, text: str) -> bool:
    return 0 <= ev_start < ev_end <= len(text) and text[ev_start:ev_end] == quote


def _run_items(
    run: RunFile,
    aligner: _Aligner,
    ontology: Ontology,
    types: dict[str, RelationType],
    canonical: Canonical,
    gold_chapters: set[str],
) -> tuple[list[Item], dict[str, Any]]:
    """Itens da execução no escopo, deduplicados, mais as contagens de quem ficou de fora."""
    text = canonical.text
    n_ev = n_located = 0
    all_items: list[Item] = []
    for n, c in enumerate(run.claims, start=1):
        it = make_item(
            f"claim#{n}", c.type_, aligner.resolve(c.subject), aligner.resolve(c.object_),
            c.class_, aligner.resolve(c.asserted_by) if c.asserted_by else None,
            c.narrative_scope, ontology, types,
        )  # fmt: skip
        it.claim, it.evidence = c, list(c.evidence)
        it.level = c.level or run.meta.level or "(sem)"
        it.lens = c.lens or run.meta.lens or "(sem)"
        for ev in c.evidence:
            n_ev += 1
            if _located(ev.start_offset, ev.end_offset, ev.quote, text):
                n_located += 1
                ch = canonical.paragraph_at(ev.start_offset).chapter
                it.chapters.add("" if ch is None else str(ch))
        all_items.append(it)

    in_scope: list[Item] = []
    out_of_scope = 0
    for it in all_items:
        if it.chapters and not (it.chapters & gold_chapters):
            out_of_scope += 1
        else:
            in_scope.append(it)

    deduped: list[Item] = []
    seen: dict[str, Item] = {}
    for it in in_scope:
        first = seen.get(it.strict_key) if it.valid_type else None
        if first is None:
            deduped.append(it)
            if it.valid_type:
                seen[it.strict_key] = it
        else:
            first.evidence.extend(it.evidence)
            first.chapters |= it.chapters
    info = {
        "claims_total": len(all_items),
        "fora_do_escopo": out_of_scope,
        "duplicadas": len(in_scope) - len(deduped),
        "tipo_invalido": sum(1 for it in deduped if not it.valid_type),
        "evidencias_total": n_ev,
        "evidencias_localizadas": n_located,
    }
    return deduped, {"info": info, "all": all_items}


# ── métricas ──────────────────────────────────────────────────────────────────


def _group_prf(
    tp: Counter[str], fp: Counter[str], fn: Counter[str]
) -> dict[str, Any]:
    keys = sorted(set(tp) | set(fp) | set(fn))
    groups = {k: _prf(tp[k], fp[k], fn[k]) for k in keys}
    micro = _prf(sum(tp.values()), sum(fp.values()), sum(fn.values()))
    f1s = [g["f1"] for g in groups.values() if g["f1"] is not None]
    macro = sum(f1s) / len(f1s) if f1s else None
    return {"por_grupo": groups, "micro": micro, "macro_f1": macro}


def _by_type(m: MatchResult) -> dict[str, Any]:
    tp: Counter[str] = Counter(_label(g) for _, g in m.exact)
    fp: Counter[str] = Counter(_label(r) for r in m.runs_unmatched_exact)
    fn: Counter[str] = Counter(_label(g) for g in m.golds_unmatched_exact)
    return _group_prf(tp, fp, fn)


def _by_family(m: MatchResult, ontology: Ontology) -> dict[str, Any]:
    fam = lambda it: parent_of(it.type_id, ontology)  # noqa: E731
    tp: Counter[str] = Counter(fam(g) for _, g in [*m.exact, *m.parent])
    fp: Counter[str] = Counter(fam(r) for r in m.runs_unmatched)
    fn: Counter[str] = Counter(fam(g) for g in m.golds_unmatched)
    out = _group_prf(tp, fp, fn)
    out["acertos_no_pai"] = len(m.parent)
    return out


def _by_attr(items: Iterable[Item], m: MatchResult, attr: str, n_gold: int) -> dict[str, Any]:
    """P/R/F1 exatos por nível ou lente: cada grupo é medido pelas claims dele
    (revocação sobre o gabarito inteiro)."""
    tp: Counter[str] = Counter(getattr(r, attr) for r, _ in m.exact)
    n: Counter[str] = Counter(getattr(r, attr) for r in items)
    out = {}
    for k in sorted(n):
        out[k] = _prf(tp[k], n[k] - tp[k], n_gold - tp[k])
    return out


def _attribution(m: MatchResult) -> dict[str, Any]:
    """Nos acertos relaxados: classe certa e, se o gabarito diz `alegada`, o mesmo
    `asserted_by`. A diferença entre as medidas mede 'atribuiu certo quem afirma'."""
    n = class_ok = ab_total = ab_ok = correct = 0
    confusion: dict[str, dict[str, int]] = {}
    wrong: list[dict[str, Any]] = []
    for r, g in m.exact:
        n += 1
        c_ok = r.class_ == g.class_
        class_ok += c_ok
        confusion.setdefault(g.class_.value, {}).setdefault(r.class_.value, 0)
        confusion[g.class_.value][r.class_.value] += 1
        a_ok = True
        if g.class_ is ClaimClass.alegada:
            ab_total += 1
            a_ok = r.asserted_by == g.asserted_by
            ab_ok += a_ok
        if c_ok and a_ok:
            correct += 1
        else:
            wrong.append(
                {
                    "relacao": g.ref,
                    "gabarito": {"classe": g.class_.value, "asserted_by": g.asserted_by},
                    "execucao": {"classe": r.class_.value, "asserted_by": r.asserted_by},
                }
            )
    return {
        "acertos_relaxados": n,
        "classe_certa": _pct(class_ok, n),
        "alegadas_no_gabarito": ab_total,
        "asserted_by_certo": _pct(ab_ok, ab_total),
        "atribuicao_correta": _pct(correct, n),
        "erradas": wrong,
        "matriz_classe": confusion,
    }


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def _proof_of_match(r: Item, g: Item, text: str) -> str:
    """Prova medida à parte da relação: a evidência do extrator coincide (se sobrepõe)
    com uma evidência alta do gabarito que apoia, ou cobre todo o conjunto declarado
    em `provas_em_conjunto`. Evidência que contradiz nunca conta como prova."""
    assert g.relation is not None
    spans = [
        (e.start_offset, e.end_offset)
        for e in r.evidence
        if _located(e.start_offset, e.end_offset, e.quote, text)
    ]
    supporting = [e for e in g.relation.evidence if e.polarity is Polarity.apoia]

    def hit(e: Any) -> bool:
        a = (e.anchor.start_offset, e.anchor.end_offset)
        return any(_overlap(a, s) for s in spans)

    if any(hit(e) for e in supporting if e.support is Support.alto):
        return "evidencia_alta"
    if g.relation.provas_em_conjunto is not None and supporting and all(hit(e) for e in supporting):
        return "conjunto"
    if any(hit(e) for e in supporting):
        return "parcial"
    return "nenhuma"


def _proofs(m: MatchResult, text: str) -> dict[str, Any]:
    cats = Counter(_proof_of_match(r, g, text) for r, g in m.exact)
    n = len(m.exact)
    ok = cats["evidencia_alta"] + cats["conjunto"]
    return {"acertos": n, "provadas": ok, "taxa": _pct(ok, n), **{k: cats[k] for k in (
        "evidencia_alta", "conjunto", "parcial", "nenhuma")}}


def _control(gold: GoldFile, all_items: list[Item]) -> dict[str, Any]:
    """Violação: qualquer claim, de qualquer tipo e direção, num par de controle
    dentro dos capítulos dele (inclui `texto_encaixado` e tipos inválidos)."""
    violations: list[dict[str, Any]] = []
    pairs = [p for p in gold.negative_pairs if not p.fictional]
    for p in pairs:
        pair = {p.subject, p.object_}
        hits = [
            {"tipo": _label(it), "capitulos": sorted(it.chapters & set(p.chapters))}
            for it in all_items
            if {it.subject, it.object_} == pair and it.chapters & set(p.chapters)
        ]
        if hits:
            violations.append({"par": [p.subject, p.object_], "claims": hits})
    return {
        "pares": len(pairs),
        "violacoes": len(violations),
        "taxa": _pct(len(violations), len(pairs)),
        "lista": violations,
    }


def _persons(gold: GoldFile, aligner: _Aligner) -> dict[str, Any]:
    gold_ids = [e.id for e in gold.entities if not e.fictional]
    hit = [i for i in gold_ids if i in aligner.aligned]
    return {
        "gabarito": len(gold_ids),
        "alinhadas": len(hit),
        "recall": _pct(len(hit), len(gold_ids)),
        "gabarito_sem_alinhamento": [i for i in gold_ids if i not in aligner.aligned],
        "execucao_sem_alinhamento": aligner.unaligned_run,
    }


def _alerts(items: list[Item], ontology: Ontology) -> list[str]:
    """Disjunções na execução (`disjoint_conflicts`): mesmo par, tipos disjuntos."""
    claims = [
        Claim.model_construct(
            id=it.ref, claim_key=it.ref, subject_id=it.subject, type_id=it.type_id,
            object_id=it.object_, claim_class=it.class_, confidence=1.0, pass_id="eval",
        )
        for it in items
        if it.valid_type
    ]  # fmt: skip
    return [
        f"disjunção: {c.claim_a.id} ({c.claim_a.type_id}) e {c.claim_b.id} "
        f"({c.claim_b.type_id}) no mesmo par"
        for c in ontology.disjoint_conflicts(claims)
    ]


# ── ponto de entrada ──────────────────────────────────────────────────────────


def evaluate(
    run: RunFile,
    gold: GoldFile,
    ontology: Ontology,
    canonical: Canonical,
) -> Report:
    types = {rt.id: rt for rt in ontology.relation_types()}
    aligner = _Aligner(gold, run)
    gold_items, unproved_items, fictional = _gold_items(gold, ontology, types)
    unproved = len(unproved_items)
    unproved_keys = frozenset(g.relaxed_key for g in unproved_items if g.valid_type)
    gold_chapters = set(gold.scope.chapters)
    run_items, extra = _run_items(run, aligner, ontology, types, canonical, gold_chapters)
    info = extra["info"]

    g_main = [g for g in gold_items if g.scope is NarrativeScope.obra]
    g_emb = [g for g in gold_items if g.scope is NarrativeScope.texto_encaixado]
    r_main = [r for r in run_items if r.scope is NarrativeScope.obra]
    r_emb = [r for r in run_items if r.scope is NarrativeScope.texto_encaixado]

    matches = {m: match(r_main, g_main, m, ontology, unproved_keys) for m in MEASURES}
    measures: dict[str, Any] = {}
    for name, m in matches.items():
        measures[name] = {
            "exato": {
                "por_tipo": _by_type(m),
                "acertos": len(m.exact),
                "ignoradas_sem_prova": m.ignored_unproved,
            },
            "familia": _by_family(m, ontology),
            "nivel": _by_attr(m.considered, m, "level", len(g_main)),
            "lente": _by_attr(m.considered, m, "lens", len(g_main)),
            "prova": _proofs(m, canonical.text),
        }

    relaxed = matches["relaxada"]
    emb = {m: match(r_emb, g_emb, m, ontology, unproved_keys) for m in MEASURES}
    gold_emb_keys = {g.strict_key for g in g_emb} | {g.relaxed_key for g in g_emb}
    wrong_scope = 0
    for r in matches["estrita"].runs_unmatched:
        if not r.valid_type or r.scope is not NarrativeScope.obra:
            continue
        twin = make_item(
            r.ref, r.type_id, r.subject, r.object_, r.class_, r.asserted_by,
            NarrativeScope.texto_encaixado, ontology, types,
        )  # fmt: skip
        wrong_scope += twin.strict_key in gold_emb_keys or twin.relaxed_key in gold_emb_keys

    calls = run.calls
    valid_calls = sum(1 for c in calls if c.json_valid)
    return {
        "run_id": run.run_id,
        "meta": run.meta.model_dump(mode="json"),
        "ontology_version": ontology.version,
        "gabarito": {
            "relacoes_positivas": len(g_main),
            "relacoes_sem_prova_ignoradas": unproved,
            "ficticias_ignoradas": fictional,
            "pares_de_controle": len([p for p in gold.negative_pairs if not p.fictional]),
        },
        "execucao": {
            **info,
            "avaliadas_obra": len(r_main),
            "texto_encaixado": len(r_emb),
        },
        "medidas": measures,
        "atribuicao": _attribution(relaxed),
        "provas": {
            "evidencias_total": info["evidencias_total"],
            "evidencias_localizadas": info["evidencias_localizadas"],
            "localizadas": _pct(info["evidencias_localizadas"], info["evidencias_total"]),
        },
        "json_valido": {
            "chamadas": len(calls),
            "validas": valid_calls,
            "taxa": _pct(valid_calls, len(calls)),
        },
        "pessoas": _persons(gold, aligner),
        "controle": _control(gold, extra["all"]),
        "texto_encaixado": {
            "gabarito": len(g_emb),
            "execucao": len(r_emb),
            "acertos_estrita": len(emb["estrita"].exact),
            "acertos_relaxada": len(emb["relaxada"].exact),
            "obra_sobre_item_encaixado": wrong_scope,
        },
        "alertas": _alerts(r_main, ontology),
    }

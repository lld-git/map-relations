"""`python -m map_relations eval` (B02 §7, §8).

Códigos de saída: 0 relatório gerado; 2 gabarito, execução ou canônico inválidos
(ou endereço de rastreador fora da máquina). Sem caminho padrão para data/golden/.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from map_relations.core.protocols import RemoteTrackingRefused, RunTracker
from map_relations.evaluation.evaluate import evaluate
from map_relations.evaluation.fill_offsets import (
    CanonicalError,
    default_canonical,
    load_canonical,
)
from map_relations.evaluation.gold import load_gold, validate_gold
from map_relations.evaluation.matching import EvalInputError
from map_relations.evaluation.report import flat_metrics, render_markdown
from map_relations.evaluation.run_file import load_run
from map_relations.ontology_io import load_ontology
from map_relations.tracking.null_tracker import NullTracker

TRACKING_ENV = "MLFLOW_TRACKING_URI"


def _err(msg: str) -> int:
    print(f"erro: {msg}", file=sys.stderr)
    return 2


def make_tracker(track: bool) -> RunTracker:
    """`NullTracker` por padrão; com --track, MlflowTracker no endereço do `.env`."""
    if not track:
        return NullTracker()
    uri = os.environ.get(TRACKING_ENV, "")
    if not uri:
        raise RemoteTrackingRefused(f"--track exige {TRACKING_ENV} (ver .env.example)")
    from map_relations.tracking.mlflow_tracker import MlflowTracker

    return MlflowTracker(uri)


def cmd_eval(
    run_path: Path,
    gold_path: Path,
    canonical: Path | None,
    reports_dir: Path,
    processed: Path,
    track: bool,
    tracker: RunTracker | None = None,
) -> int:
    if track and tracker is None:  # falha cedo: nada é calculado com endereço recusado
        try:
            tracker = make_tracker(True)
        except RemoteTrackingRefused as exc:
            return _err(str(exc))
    ontology = load_ontology()
    try:
        canon = load_canonical(canonical if canonical is not None else default_canonical(processed))
        gold = load_gold(gold_path)
        run = load_run(run_path)
    except (CanonicalError, OSError, ValueError, ValidationError) as exc:
        return _err(str(exc).splitlines()[0])
    gold_report = validate_gold(gold, ontology, canon)
    if not gold_report.ok:
        for e in gold_report.errors:
            print(f"erro: gabarito: {e}", file=sys.stderr)
        return 2
    try:
        report = evaluate(run, gold, ontology, canon)
    except EvalInputError as exc:
        for e in exc.errors:
            print(f"erro: {e}", file=sys.stderr)
        return 2

    out = reports_dir / run.run_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"relatório: {out}/report.md")

    if tracker is not None:
        _track(
            tracker, report, run.run_id, gold.source.content_hash, canon,
            gold.ontology_version, out,
        )  # fmt: skip
    return 0


def _track(
    tr: RunTracker,
    report: dict,  # type: ignore[type-arg]
    run_id: str,
    gold_hash: str,
    canon: object,
    ontology_version: int,
    out: Path,
) -> None:
    meta = report["meta"]
    params: dict[str, str | int | float | bool] = {
        "gold_hash": gold_hash,
        "canonical_hash": "sha256:" + canon.source.content_hash,  # type: ignore[attr-defined]
        "ontology_version": ontology_version,
        "model": meta["model"],
        "prompt_version": meta["prompt_version"],
        "level": meta["level"] or "(sem)",
        "lens": meta["lens"] or "(sem)",
    }
    for k, v in meta["parameters"].items():
        params[f"param.{k}"] = v
    tr.start(run_id)
    try:
        tr.set_tags({"run_id": run_id})
        tr.log_params(params)
        tr.log_metrics(flat_metrics(report))
        tr.log_artifact(out / "report.md")
        tr.log_artifact(out / "report.json")
    except Exception:
        tr.end("FAILED")
        raise
    tr.end("FINISHED")

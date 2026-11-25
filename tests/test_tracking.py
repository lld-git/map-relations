"""RunTracker (B02 §8): contrato, recusa de endereço fora da máquina, adaptadores."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from map_relations.core.protocols import (
    RemoteTrackingRefused,
    RunTracker,
    check_local_tracking_uri,
)
from map_relations.evaluation.eval_cli import cmd_eval, make_tracker
from map_relations.tracking.mlflow_tracker import MlflowTracker
from map_relations.tracking.null_tracker import NullTracker
from tests.eval_helpers import (
    Q_BOLSO,
    Q_BRUNO,
    Q_CARLA,
    Q_FULANO,
    Q_VIGIA,
    make_canon,
    make_gold,
    make_run,
)
from tests.gold_helpers import write_processed

CANON = make_canon()


@pytest.mark.parametrize(
    "uri",
    [
        "http://mlflow:5000",
        "http://localhost:5010",
        "http://127.0.0.1:5010/",
        "https://LOCALHOST:5010",
        "file:///tmp/mlruns",
        "sqlite:///mlflow.db",
        "/tmp/mlruns",
        "mlruns",
    ],
)
def test_local_addresses_are_accepted(uri):
    assert check_local_tracking_uri(uri) == uri


@pytest.mark.parametrize(
    "uri",
    [
        "",
        "http://mlflow.exemplo.com:5000",
        "http://localhost.exemplo.com:5010",
        "http://127.0.0.1@exemplo.com:5010",  # o host de verdade é exemplo.com
        "http://10.0.0.5:5000",
        "http://0.0.0.0:5000",
        "http://[::1]:5000",
        "https://exemplo.com",
        "databricks",
        "databricks://perfil",
        "s3://balde/mlruns",
        "postgresql://u:s@banco.exemplo.com/mlflow",
        "ftp://localhost/x",
        "file://servidor.exemplo.com/mlruns",
    ],
)
def test_addresses_outside_the_machine_are_refused(uri):
    with pytest.raises(RemoteTrackingRefused):
        check_local_tracking_uri(uri)


def test_mlflow_tracker_refuses_remote_address_before_connecting():
    with pytest.raises(RemoteTrackingRefused):
        MlflowTracker("http://mlflow.exemplo.com:5000")


def test_make_tracker_default_is_null_and_track_needs_an_address(monkeypatch):
    assert isinstance(make_tracker(False), NullTracker)
    monkeypatch.delenv("MLFLOW_TRACKING_URI", raising=False)
    with pytest.raises(RemoteTrackingRefused, match="MLFLOW_TRACKING_URI"):
        make_tracker(True)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://exemplo.com:5000")
    with pytest.raises(RemoteTrackingRefused):
        make_tracker(True)


def test_null_tracker_satisfies_the_contract():
    t = NullTracker()
    assert isinstance(t, RunTracker)
    t.start("x")
    t.log_params({"a": 1})
    t.log_metrics({"m": 1.0})
    t.set_tags({"k": "v"})
    t.end()


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def start(self, run_name: str) -> None:
        self.calls.append(("start", run_name))

    def log_params(self, params: Mapping[str, str | int | float | bool]) -> None:
        self.calls.append(("params", dict(params)))

    def log_metrics(self, metrics: Mapping[str, float]) -> None:
        self.calls.append(("metrics", dict(metrics)))

    def log_artifact(self, path: Path) -> None:
        assert path.is_file()
        self.calls.append(("artifact", path.name))

    def set_tags(self, tags: Mapping[str, str]) -> None:
        self.calls.append(("tags", dict(tags)))

    def end(self, status: str = "FINISHED") -> None:
        self.calls.append(("end", status))


def _eval_with(tmp_path: Path, tracker) -> int:
    proc = write_processed(tmp_path / "w", CANON)
    run_p, gold_p = tmp_path / "run.json", tmp_path / "gold.json"
    run_p.write_text(json.dumps(make_run(CANON)), encoding="utf-8")
    gold_p.write_text(json.dumps(make_gold(CANON)), encoding="utf-8")
    return cmd_eval(run_p, gold_p, proc, tmp_path / "reports", tmp_path / "x", True, tracker)


def test_eval_track_registers_params_metrics_and_report_as_artifact(tmp_path):
    rec = Recorder()
    assert _eval_with(tmp_path, rec) == 0
    kinds = [c[0] for c in rec.calls]
    assert kinds == ["start", "tags", "params", "metrics", "artifact", "artifact", "end"]
    params = rec.calls[2][1]
    assert params["gold_hash"] == "sha256:" + CANON.source.content_hash
    assert params["canonical_hash"] == "sha256:" + CANON.source.content_hash
    assert params["ontology_version"] >= 1
    assert (params["model"], params["prompt_version"]) == ("modelo-falso", "p0")
    assert (params["level"], params["lens"], params["param.temperature"]) == ("N1", "padrao", 0.0)
    metrics = rec.calls[3][1]
    assert metrics["p.estrita.micro"] == pytest.approx(3 / 11)
    assert metrics["controle.violacoes"] == 1.0
    assert rec.calls[-1] == ("end", "FINISHED")
    assert {c[1] for c in rec.calls if c[0] == "artifact"} == {"report.md", "report.json"}


def test_protected_text_goes_only_to_the_artifact(tmp_path):
    rec = Recorder()
    _eval_with(tmp_path, rec)
    seen = json.dumps([c for c in rec.calls if c[0] != "artifact"], ensure_ascii=False)
    for quote in (Q_VIGIA, Q_CARLA, Q_BOLSO, Q_BRUNO, Q_FULANO, "Fulano", "Dora", "Ana", "Bruno"):
        assert quote not in seen, quote
    # o texto da obra nunca é parâmetro, métrica nem tag; nomes de métrica são só tipos/medidas
    assert all(len(str(v)) < 100 for v in rec.calls[2][1].values())


def test_remote_address_stops_before_any_work(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://mlflow.exemplo.com:5000")
    proc = write_processed(tmp_path / "w", CANON)
    run_p, gold_p = tmp_path / "run.json", tmp_path / "gold.json"
    run_p.write_text(json.dumps(make_run(CANON)), encoding="utf-8")
    gold_p.write_text(json.dumps(make_gold(CANON)), encoding="utf-8")
    code = cmd_eval(run_p, gold_p, proc, tmp_path / "reports", tmp_path / "x", True)
    assert code == 2
    assert "fora da máquina" in capsys.readouterr().err
    assert not (tmp_path / "reports").exists()  # nem o relatório foi gravado


def test_tracker_failure_marks_the_run_failed(tmp_path):
    class Boom(Recorder):
        def log_metrics(self, metrics):
            raise RuntimeError("falha")

    rec = Boom()
    with pytest.raises(RuntimeError):
        _eval_with(tmp_path, rec)
    assert rec.calls[-1] == ("end", "FAILED")


def test_mlflow_adapter_writes_to_a_file_store(tmp_path, monkeypatch):
    """Sem servidor (CI): o adaptador grava em `file://` num diretório temporário.

    O MLflow 3.x deixou o armazenamento em arquivos em modo de manutenção e o
    bloqueia por padrão; só este teste opta por ele (o servidor real usa SQLite).
    """
    import mlflow

    monkeypatch.setenv("MLFLOW_ALLOW_FILE_STORE", "true")

    store = tmp_path / "mlruns"
    uri = store.as_uri()
    tracker = MlflowTracker(uri, experiment="teste")
    assert isinstance(tracker, RunTracker)
    artifact = tmp_path / "report.md"
    artifact.write_text("# relatório sintético\n", encoding="utf-8")
    tracker.start("execucao-1")
    tracker.set_tags({"run_id": "execucao-1"})
    tracker.log_params({"model": "modelo-falso", "temperature": 0.0})
    tracker.log_metrics({"p.estrita.micro": 0.5, "controle.violacoes": 1.0})
    tracker.log_artifact(artifact)
    tracker.end()

    client = mlflow.tracking.MlflowClient(uri)
    exp = client.get_experiment_by_name("teste")
    assert exp is not None
    (run,) = client.search_runs([exp.experiment_id])
    assert run.data.params["model"] == "modelo-falso"
    assert run.data.metrics["p.estrita.micro"] == 0.5
    assert run.data.tags["run_id"] == "execucao-1"
    assert run.info.status == "FINISHED"
    assert [a.path for a in client.list_artifacts(run.info.run_id)] == ["report.md"]

"""Adaptador MLflow do `RunTracker` (B02 §8, ADR 013).

`mlflow-skinny` é dependência de dev e só é importada ao criar o adaptador
(import local): o domínio e a imagem de produção nunca a carregam.
O endereço passa por `check_local_tracking_uri` antes de qualquer conexão.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from map_relations.core.protocols import check_local_tracking_uri

EXPERIMENT = "map-relations-eval"
_MAX_PARAM_LEN = 250


class MlflowTracker:
    def __init__(self, tracking_uri: str, experiment: str = EXPERIMENT) -> None:
        self._uri = check_local_tracking_uri(tracking_uri)
        # a imagem não tem git; sem isto o MLflow imprime um aviso a cada execução
        os.environ.setdefault("GIT_PYTHON_REFRESH", "quiet")
        import mlflow  # import local: dependência só de dev

        self._mlflow: Any = mlflow
        mlflow.set_tracking_uri(self._uri)
        mlflow.set_experiment(experiment)
        self._active = False

    def start(self, run_name: str) -> None:
        self._mlflow.start_run(run_name=run_name)
        self._active = True

    def log_params(self, params: Mapping[str, str | int | float | bool]) -> None:
        self._mlflow.log_params({k: str(v)[:_MAX_PARAM_LEN] for k, v in params.items()})

    def log_metrics(self, metrics: Mapping[str, float]) -> None:
        self._mlflow.log_metrics({k: float(v) for k, v in metrics.items()})

    def log_artifact(self, path: Path) -> None:
        self._mlflow.log_artifact(str(path))

    def set_tags(self, tags: Mapping[str, str]) -> None:
        self._mlflow.set_tags(dict(tags))

    def end(self, status: str = "FINISHED") -> None:
        if self._active:
            self._mlflow.end_run(status=status)
            self._active = False

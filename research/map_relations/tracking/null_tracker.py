"""Rastreador que não faz nada: o padrão do `eval` e dos testes."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


class NullTracker:
    def start(self, run_name: str) -> None:
        return None

    def log_params(self, params: Mapping[str, str | int | float | bool]) -> None:
        return None

    def log_metrics(self, metrics: Mapping[str, float]) -> None:
        return None

    def log_artifact(self, path: Path) -> None:
        return None

    def set_tags(self, tags: Mapping[str, str]) -> None:
        return None

    def end(self, status: str = "FINISHED") -> None:
        return None

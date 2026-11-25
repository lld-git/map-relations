"""Configuração do MLflow e do que não pode ir para o Git (B02 §8, §13 item 5)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
SERVICE = COMPOSE["services"]["mlflow"]


def _lines(name: str) -> list[str]:
    return (ROOT / name).read_text(encoding="utf-8").splitlines()


def test_mlflow_is_published_only_on_loopback_port_5010():
    assert SERVICE["ports"] == ["127.0.0.1:5010:5000"]


def test_mlflow_runs_only_under_its_profile():
    assert SERVICE["profiles"] == ["mlflow"]


def test_mlflow_data_lives_in_the_ignored_folder():
    assert "./mlflow_data:/mlflow" in SERVICE["volumes"]
    assert "mlflow_data/" in _lines(".gitignore")
    assert "mlflow_data/" in _lines(".dockerignore")


def test_server_version_is_pinned_and_equals_the_client_version():
    image = SERVICE["image"]
    version = image.rsplit(":v", 1)[1]
    assert image == f"ghcr.io/mlflow/mlflow:v{version}"  # exata, sem latest
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'"mlflow-skinny=={version}"' in pyproject


def test_protected_folders_are_ignored_by_git():
    ignore = _lines(".gitignore")
    assert "data/golden/" in ignore
    assert "eval/reports/*" in ignore
    assert "!eval/reports/.gitkeep" in ignore  # a pasta existe; o conteúdo não vai
    assert "mlflow_data/" in ignore


def test_reports_folder_is_tracked_only_through_gitkeep():
    assert (ROOT / "eval" / "reports" / ".gitkeep").is_file()


def test_env_example_points_to_a_local_address():
    from map_relations.core.protocols import check_local_tracking_uri

    line = next(
        ln for ln in _lines(".env.example") if ln.startswith("MLFLOW_TRACKING_URI=")
    )
    check_local_tracking_uri(line.split("=", 1)[1])

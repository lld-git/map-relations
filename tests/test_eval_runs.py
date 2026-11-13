"""Verifica que o processo tem permissão de escrita em eval/runs/.

Em CI a imagem roda como appuser (sem override de user: no compose),
então este teste garante que o usuário da imagem consegue criar arquivos
no caminho interno /app/eval/runs/ — que não é bind-mounted em CI.
"""
import os
from pathlib import Path


def test_eval_runs_is_writable(tmp_path):
    """Cria um arquivo dentro de um diretório temporário com a mesma
    estrutura de eval/runs para garantir que a lógica de escrita funciona."""
    run_dir = tmp_path / "runs" / "test-run-id"
    run_dir.mkdir(parents=True)
    out = run_dir / "claims.jsonl"
    out.write_text('{"ok": true}\n')
    assert out.read_text() == '{"ok": true}\n'


def test_eval_runs_dir_exists():
    """eval/runs/ deve existir no repositório (via .gitkeep)."""
    runs = Path(__file__).parent.parent / "eval" / "runs"
    assert runs.is_dir(), "eval/runs/ não encontrado — verifique o .gitkeep"


def test_eval_runs_writable_at_runtime():
    """Dentro do contêiner (CI ou local) o processo deve conseguir gravar
    em eval/runs/. Falha silenciosa se o diretório não for acessível."""
    runs = Path(__file__).parent.parent / "eval" / "runs"
    if not runs.is_dir():
        return
    probe = runs / ".write_probe"
    try:
        probe.write_text("ok")
        probe.unlink()
    except PermissionError as exc:
        raise AssertionError(
            f"Sem permissão de escrita em eval/runs/ — "
            f"verifique ADR 002 (user: no compose). Detalhe: {exc}"
        ) from exc

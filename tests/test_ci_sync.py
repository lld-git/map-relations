"""`make ci` e .github/workflows/ci.yml não podem divergir em silêncio (B02 §2)."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
MAKEFILE = ROOT / "Makefile"

# (job do ci.yml, alvo do Makefile, variável com a tag no Makefile, tag no ci.yml)
JOBS = [
    ("test", "ci-test", "CI_DEV", "dev"),
    ("build-prod", "ci-prod", "CI_PROD", "prod"),
]


def _workflow_job(job: str) -> dict:
    return yaml.safe_load(CI_YML.read_text(encoding="utf-8"))["jobs"][job]


def _workflow_commands(job: str, tag: str) -> list[str]:
    """Comandos `docker run --rm <tag> …` do job, na ordem; qualquer outro run é erro."""
    out = []
    for step in _workflow_job(job)["steps"]:
        if "run" not in step:
            continue
        m = re.fullmatch(rf"docker run --rm {re.escape(tag)} (.+)", step["run"].strip())
        assert m, f"{job}: passo fora do padrão `docker run --rm {tag} …`: {step['run']!r}"
        out.append(m.group(1))
    return out


def _workflow_target(job: str) -> str:
    build = next(s for s in _workflow_job(job)["steps"] if "build-push-action" in s.get("uses", ""))
    return build["with"]["target"]


def _workflow_tag(job: str) -> str:
    build = next(s for s in _workflow_job(job)["steps"] if "build-push-action" in s.get("uses", ""))
    return build["with"]["tags"]


def _recipe(target: str) -> list[str]:
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{target}:"))
    out = []
    for line in lines[start + 1 :]:
        if not line.startswith("\t"):
            break
        out.append(line.strip())
    return out


def _make_commands(target: str, var: str) -> list[str]:
    out = []
    for line in _recipe(target):
        m = re.fullmatch(rf"docker run --rm \$\({var}\) (.+)", line)
        if m:
            out.append(m.group(1))
    return out


def _make_var(name: str) -> str:
    m = re.search(rf"^{name} = (\S+)$", MAKEFILE.read_text(encoding="utf-8"), re.MULTILINE)
    assert m, f"{name} não definido no Makefile"
    return m.group(1)


@pytest.mark.parametrize(("job", "target", "var", "stage"), JOBS)
def test_make_ci_runs_same_commands_as_workflow(job, target, var, stage):
    wf = _workflow_commands(job, _workflow_tag(job))
    mk = _make_commands(target, var)
    assert wf, f"{job}: nenhum comando docker run encontrado no ci.yml"
    assert mk == wf, f"`make {target}` diverge do job `{job}` de ci.yml"


@pytest.mark.parametrize(("job", "target", "var", "stage"), JOBS)
def test_make_ci_builds_same_stage_as_workflow(job, target, var, stage):
    assert _workflow_target(job) == stage
    build = next(line for line in _recipe(target) if "docker build" in line)
    assert f"--target {stage} " in build
    assert f"-t $({var}) " in build


def test_make_ci_prod_tag_matches_workflow():
    # princípio 14: a tag da prod é a mesma do ci.yml; a da dev é local (maprelations-app)
    assert _make_var("CI_PROD") == _workflow_tag("build-prod")
    assert _make_var("CI_DEV") == "maprelations-app"


def test_make_ci_runs_both_jobs_then_prunes():
    assert _recipe("ci") == ["docker image prune -f"]
    lines = MAKEFILE.read_text(encoding="utf-8").splitlines()
    assert next(line for line in lines if line.startswith("ci:")).split() == [
        "ci:",
        "ci-test",
        "ci-prod",
    ]


def test_make_ci_context_is_git_index_without_volumes():
    for target in ("ci-test", "ci-prod"):
        recipe = _recipe(target)
        assert recipe[0].startswith("$(CI_CONTEXT) | docker build")
        assert not any(" -v " in line or "--user" in line or " -u " in line for line in recipe)
    context = re.search(r"^CI_CONTEXT = (.+)$", MAKEFILE.read_text(encoding="utf-8"), re.M)
    assert context and context.group(1).startswith("git archive")

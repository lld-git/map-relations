"""Protocols do core e coerência dos JSON Schemas gerados."""

from pathlib import Path

from map_relations.core.protocols import (
    LlmCapabilities,
    LlmEngine,
    LlmRequest,
    LlmResponse,
)
from scripts.generate_schemas import DOMAIN_MODELS, SCHEMAS_DIR, _to_kebab, render


class FakeEngine:
    @property
    def id(self) -> str:
        return "fake"

    @property
    def capabilities(self) -> LlmCapabilities:
        return LlmCapabilities(
            json_schema=True,
            max_context_tokens=8192,
            runs_locally=True,
            data_policy_note="teste",
        )

    async def complete(self, req: LlmRequest) -> LlmResponse:
        return LlmResponse(text="ok", finish_reason="stop")


def test_fake_engine_satisfies_protocol():
    assert isinstance(FakeEngine(), LlmEngine)


def test_all_domain_schemas_exist_and_match():
    """Mesma verificação do CI: schema gravado == schema gerado do modelo."""
    for model in DOMAIN_MODELS:
        path = SCHEMAS_DIR / f"{_to_kebab(model.__name__)}.json"
        assert path.exists(), f"faltando: {path.name} — rode scripts/generate_schemas.py"
        assert path.read_text(encoding="utf-8") == render(model), (
            f"desatualizado: {path.name} — rode scripts/generate_schemas.py"
        )


def test_claim_schema_uses_class_alias():
    schema_path = Path(SCHEMAS_DIR) / "claim.json"
    content = schema_path.read_text(encoding="utf-8")
    assert '"class"' in content
    assert "claim_class" not in content

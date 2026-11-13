"""Layout de data/processed/ por hash do PDF (ADR 008, §5).

data/processed/<hash_pdf>/
  source.json                              nome, kind, hash do arquivo
  docling/<versao>-<opcoes>/docling.json   cache da conversão cara
  pdf_loader/raw.json                      rota alternativa, se usada
  documento.md                             FONTE, revisada pelo humano
  canonical.txt / ingest.json / report.md  derivados do .md
  comparacao_docling.md                    comparação entre rotas

O hash canônico fica dentro de ingest.json; o nome da pasta usa o hash do
arquivo de origem (estável mesmo quando o pipeline muda).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

# Mantidos em sincronia com docker/docling/Dockerfile e com o alvo
# "docling" do Makefile. Mudar versão ou opções cria um cache novo.
DOCLING_VERSION = "2.150.0"
DOCLING_OPTIONS_SLUG = "noocr-notables-imgplaceholder-b1"
DOCLING_CACHE_KEY = f"{DOCLING_VERSION}-{DOCLING_OPTIONS_SLUG}"


def file_hash(path: Path) -> str:
    """sha256 dos bytes do arquivo de origem (chave da pasta em processed/)."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ProcessedStore:
    def __init__(self, processed_dir: Path) -> None:
        self.processed_dir = processed_dir

    def dir_for(self, source_hash: str) -> Path:
        return self.processed_dir / source_hash

    def docling_cache_dir(self, source_hash: str) -> Path:
        """Pasta do cache do Docling para a versão+opções correntes.
        Contém um pages_XXXX-YYYY.json por faixa (B04c)."""
        return self.dir_for(source_hash) / "docling" / DOCLING_CACHE_KEY

    def docling_range(self, source_hash: str, start: int, end: int) -> Path:
        return self.docling_cache_dir(source_hash) / f"pages_{start:04d}-{end:04d}.json"

    def docling_range_files(self, source_hash: str) -> list[Path]:
        """Faixas já convertidas, em ordem de página."""
        d = self.docling_cache_dir(source_hash)
        return sorted(d.glob("pages_*.json")) if d.is_dir() else []

    def documento_md(self, source_hash: str) -> Path:
        return self.dir_for(source_hash) / "documento.md"

    def write_source_json(self, source_hash: str, *, file_name: str, kind: str) -> None:
        d = self.dir_for(source_hash)
        d.mkdir(parents=True, exist_ok=True)
        (d / "source.json").write_text(
            json.dumps(
                {"file": file_name, "kind": kind, "sha256": source_hash},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    def orphans(self, raw_dir: Path) -> list[Path]:
        """Pastas órfãs: hash sem arquivo correspondente em data/raw/ e
        caches docling de chaves antigas. Não apaga nada — só lista."""
        current_hashes = {
            file_hash(p) for p in sorted(raw_dir.iterdir()) if p.is_file()
        } if raw_dir.is_dir() else set()
        result: list[Path] = []
        if not self.processed_dir.is_dir():
            return result
        for d in sorted(self.processed_dir.iterdir()):
            if not d.is_dir():
                continue
            if d.name not in current_hashes:
                result.append(d)
                continue
            docling_dir = d / "docling"
            if docling_dir.is_dir():
                for cache in sorted(docling_dir.iterdir()):
                    if cache.is_dir() and cache.name != DOCLING_CACHE_KEY:
                        result.append(cache)
        return result

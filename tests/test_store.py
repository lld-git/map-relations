"""Layout de data/processed/ por hash do arquivo e limpeza de órfãs (ADR 008)."""

import json

from map_relations.ingest.store import DOCLING_CACHE_KEY, ProcessedStore, file_hash


def test_file_hash_deterministic(tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"conteudo")
    g = tmp_path / "b.pdf"
    g.write_bytes(b"conteudo")
    assert file_hash(f) == file_hash(g)
    g.write_bytes(b"outro")
    assert file_hash(f) != file_hash(g)


def test_source_json_and_paths(tmp_path):
    store = ProcessedStore(tmp_path / "processed")
    store.write_source_json("abc123", file_name="livro.pdf", kind="pdf")
    data = json.loads((tmp_path / "processed/abc123/source.json").read_text())
    assert data == {"file": "livro.pdf", "kind": "pdf", "sha256": "abc123"}
    assert store.docling_cache_dir("abc123") == (
        tmp_path / "processed/abc123/docling" / DOCLING_CACHE_KEY
    )


def test_docling_range_files_sorted_by_page(tmp_path):
    store = ProcessedStore(tmp_path / "processed")
    assert store.docling_range_files("h") == []
    for start, end in [(41, 80), (1, 40), (81, 90)]:
        p = store.docling_range(start=start, end=end, source_hash="h")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{}")
    files = store.docling_range_files("h")
    assert [f.name for f in files] == [
        "pages_0001-0040.json",
        "pages_0041-0080.json",
        "pages_0081-0090.json",
    ]


def test_orphans_detected_but_not_deleted(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "vivo.pdf").write_bytes(b"vivo")
    alive_hash = file_hash(raw / "vivo.pdf")

    processed = tmp_path / "processed"
    store = ProcessedStore(processed)
    # pasta viva com cache atual e um cache de chave antiga
    (processed / alive_hash / "docling" / DOCLING_CACHE_KEY).mkdir(parents=True)
    old_cache = processed / alive_hash / "docling" / "1.0.0-antigo"
    old_cache.mkdir(parents=True)
    # pasta órfã (hash sem arquivo em raw/)
    orphan_dir = processed / "deadbeef"
    orphan_dir.mkdir()

    orphans = store.orphans(raw)
    assert orphan_dir in orphans
    assert old_cache in orphans
    assert processed / alive_hash not in orphans
    assert orphan_dir.exists()  # listar não apaga

"""CLI: caminhos de erro saem com código diferente de zero."""

from map_relations.__main__ import main


def test_ingest_missing_file_returns_nonzero():
    assert main(["ingest", "nao-existe.pdf"]) == 2


def test_ingest_outside_data_raw_returns_nonzero(tmp_path):
    outside = tmp_path / "fora.pdf"
    outside.write_bytes(b"%PDF-1.4")
    assert main(["ingest", str(outside)]) == 2

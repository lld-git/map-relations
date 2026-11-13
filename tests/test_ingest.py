from map_relations.ingest.document import Source, compute_text_hash


def test_source_generates_id():
    s = Source(title="O Processo", kind="pdf", content_hash="abc123")
    assert s.id != ""
    assert len(s.id) == 36  # UUID4


def test_source_two_instances_have_different_ids():
    s1 = Source(title="doc", kind="pdf", content_hash="x")
    s2 = Source(title="doc", kind="pdf", content_hash="x")
    assert s1.id != s2.id


def test_compute_text_hash_is_deterministic():
    text = "Franz Kafka"
    assert compute_text_hash(text) == compute_text_hash(text)


def test_compute_text_hash_differs_for_different_content():
    assert compute_text_hash("a") != compute_text_hash("b")

from scripts.fetch_kb import load_sources
from scripts.ingest_kb import chunk, seed_documents


def test_sources_use_known_slugs_and_unique_ids():
    sources = load_sources()  # raises on unknown crop/disease slugs
    ids = [s["id"] for s in sources]
    assert len(ids) == len(set(ids))
    assert len(sources) >= 40


def test_seed_remedies_chunk_with_metadata():
    docs = seed_documents()
    assert len(docs) == 38
    meta, body = next(d for d in docs if d[0]["crop"] == "tomato" and d[0]["disease"] == "late_blight")
    ids, texts, metadatas = chunk(meta, body)
    assert ids[0] == "seed-tomato-late_blight:0"
    assert texts[0].startswith("AuraFarm remedy notes: Tomato late blight")
    assert metadatas[0]["crop"] == "tomato" and metadatas[0]["disease"] == "late_blight"

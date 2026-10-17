import chromadb
import pytest

from app.services.knowledge_base import KnowledgeBase
from tests.fakes import hashing_embedder


@pytest.fixture
def kb():
    client = chromadb.EphemeralClient()
    name = f"test_{id(client)}"
    kb = KnowledgeBase(client, name, hashing_embedder)
    docs = [
        ("t-eb", "Early blight of tomato: remove lower leaves, apply chlorothalonil or copper fungicide.", "tomato", "early_blight"),
        ("t-lb", "Late blight of tomato: destroy infected plants, apply mancozeb fungicide before rain.", "tomato", "late_blight"),
        ("t-gen", "Tomato general care: rotate crops, mulch, water at the base, stake plants.", "tomato", "general"),
        ("p-eb", "Early blight of potato: plant certified seed and apply fungicide after canopy closure.", "potato", "early_blight"),
    ]
    kb.upsert(
        ids=[d[0] for d in docs],
        documents=[d[1] for d in docs],
        metadatas=[{"crop": d[2], "disease": d[3], "title": d[0], "source_url": "", "source_org": "test"} for d in docs],
    )
    yield kb
    client.delete_collection(name)


def test_exact_scope_comes_first(kb):
    hits = kb.search("fungicide for early blight", crop="tomato", disease="early_blight", k=1)
    assert [(h["crop"], h["disease"], h["match"]) for h in hits] == [("tomato", "early_blight", "crop_and_disease")]


def test_widens_to_crop_then_never_leaks_other_crops_first(kb):
    hits = kb.search("fungicide blight", crop="tomato", disease="early_blight", k=3)
    assert hits[0]["match"] == "crop_and_disease"
    assert {h["crop"] for h in hits} == {"tomato"}
    assert {h["match"] for h in hits[1:]} == {"crop"}


def test_unscoped_search_without_diagnosis(kb):
    hits = kb.search("certified seed potato", k=2)
    assert hits and hits[0]["crop"] == "potato"
    assert all(h["match"] == "unscoped" for h in hits)


def test_empty_collection_returns_nothing():
    client = chromadb.EphemeralClient()
    assert KnowledgeBase(client, "empty_kb", hashing_embedder).search("anything") == []

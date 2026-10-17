"""Chunks kb/docs/*.md and kb/remedies_seed.json and upserts them into the Chroma knowledge base.

Usage (from Backend/):  python -m scripts.ingest_kb [--reset]
"""

import argparse
import json
from pathlib import Path

import chromadb
import yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.services.knowledge_base import KnowledgeBase, SentenceTransformerEmbedder
from app.services.labels import get_label

KB_DIR = Path(__file__).resolve().parent.parent / "kb"
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)


def parse_doc(path: Path) -> tuple[dict, str]:
    raw = path.read_text()
    _, front_matter, body = raw.split("---", 2)
    return yaml.safe_load(front_matter), body.strip()


def seed_documents() -> list[tuple[dict, str]]:
    """The hand-written remedies that shipped with AuraFarm, one document per disease."""
    seed = json.loads((KB_DIR / "remedies_seed.json").read_text())
    docs = []
    for label, entry in seed.items():
        plant = get_label(label)
        lines = [f"# {plant.display}", "", entry.get("description", "")]
        for heading, key in (("Organic treatment", "organic_treatment"), ("Chemical treatment", "chemical_treatment")):
            if entry.get(key):
                lines += ["", f"## {heading}", *[f"- {item}" for item in entry[key]]]
        meta = {
            "id": f"seed-{plant.crop}-{plant.disease}",
            "title": f"AuraFarm remedy notes: {plant.display}",
            "source_url": "",
            "source_org": "AuraFarm",
            "crop": plant.crop,
            "disease": plant.disease,
        }
        docs.append((meta, "\n".join(lines)))
    return docs


def chunk(meta: dict, body: str) -> tuple[list[str], list[str], list[dict]]:
    ids, texts, metadatas = [], [], []
    for i, piece in enumerate(SPLITTER.split_text(body)):
        ids.append(f"{meta['id']}:{i}")
        # Prefix the title so each chunk carries its topic into the embedding.
        texts.append(f"{meta['title']}\n\n{piece}")
        metadatas.append({**meta, "chunk": i})
    return ids, texts, metadatas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="delete the collection before ingesting")
    args = parser.parse_args()

    settings = get_settings()
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    if args.reset and settings.kb_collection in [c.name for c in client.list_collections()]:
        client.delete_collection(settings.kb_collection)
    kb = KnowledgeBase(client, settings.kb_collection, SentenceTransformerEmbedder(settings.embedding_model))

    documents = seed_documents() + [parse_doc(p) for p in sorted((KB_DIR / "docs").glob("*.md"))]
    total = 0
    for meta, body in documents:
        ids, texts, metadatas = chunk(meta, body)
        if ids:
            kb.upsert(ids, texts, metadatas)
            total += len(ids)
    print(f"Ingested {total} chunks from {len(documents)} documents into '{settings.kb_collection}'.")


if __name__ == "__main__":
    main()

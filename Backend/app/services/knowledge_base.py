"""Remedy knowledge base in ChromaDB. Every chunk is tagged with the same crop/disease slugs the
classifier produces (see labels.py), so retrieval can be scoped to the diagnosed problem."""

import asyncio
from collections.abc import Callable
from functools import lru_cache

import chromadb

from app.config import get_settings
from app.services.labels import GENERAL

Embedder = Callable[[list[str]], list[list[float]]]

# bge models retrieve better when queries (not documents) carry this instruction.
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
# Cosine distance above which an unfiltered hit is treated as off-topic.
_MAX_UNSCOPED_DISTANCE = 0.55


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def __call__(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


class KnowledgeBase:
    def __init__(
        self, client: chromadb.ClientAPI, collection_name: str, embed: Embedder, query_prefix: str = ""
    ):
        self._embed = embed
        self._query_prefix = query_prefix
        self._collection = client.get_or_create_collection(
            collection_name, configuration={"hnsw": {"space": "cosine"}}, embedding_function=None
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def count(self) -> int:
        return self._collection.count()

    def upsert(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        self._collection.upsert(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=self._embed(documents)
        )

    def search(
        self, query: str, crop: str | None = None, disease: str | None = None, k: int = 5
    ) -> list[dict]:
        """Retrieves chunks for the exact crop+disease first, then widens to the crop (plus general
        material), then to the whole collection, until k chunks are found."""
        if self.count() == 0:
            return []

        scopes: list[tuple[str, dict | None]] = []
        if crop and disease:
            scopes.append(("crop_and_disease", {"$and": [{"crop": crop}, {"disease": disease}]}))
        if crop:
            scopes.append(("crop", {"crop": {"$in": [crop, GENERAL]}}))
        scopes.append(("unscoped", None))

        query_embedding = self._embed([self._query_prefix + query])[0]
        hits: list[dict] = []
        seen: set[str] = set()
        for scope, where in scopes:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where,
                include=["documents", "metadatas", "distances"],
            )
            for chunk_id, doc, meta, distance in zip(
                result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]
            ):
                if chunk_id in seen or (scope == "unscoped" and distance > _MAX_UNSCOPED_DISTANCE):
                    continue
                seen.add(chunk_id)
                hits.append(
                    {
                        "text": doc,
                        "title": meta.get("title"),
                        "source_url": meta.get("source_url"),
                        "source_org": meta.get("source_org"),
                        "crop": meta.get("crop"),
                        "disease": meta.get("disease"),
                        "match": scope,
                        "distance": round(distance, 3),
                    }
                )
            if len(hits) >= k:
                break
        return hits[:k]

    async def asearch(self, *args, **kwargs) -> list[dict]:
        return await asyncio.to_thread(self.search, *args, **kwargs)


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    settings = get_settings()
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    query_prefix = BGE_QUERY_INSTRUCTION if "bge" in settings.embedding_model.lower() else ""
    return KnowledgeBase(
        client, settings.kb_collection, SentenceTransformerEmbedder(settings.embedding_model), query_prefix
    )

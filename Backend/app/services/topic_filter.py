"""Optional embedding-based off-topic filter (TOPIC_FILTER_ENABLED=true).

Compares a message with example on-topic and off-topic requests using the knowledge base's
embedding model (~10 ms, no API call). Short messages always pass, so follow-ups like "yes" or
"what about the other one?" are never blocked. Calibrate with `python -m scripts.check_topics`.
"""

import asyncio
from functools import lru_cache

from app.config import get_settings

ON_TOPIC = [
    "how do I treat this plant disease",
    "what fungicide should I spray on my crop",
    "why are the leaves of my tomato plant turning yellow",
    "how to prevent blight in potatoes",
    "is it safe to spray pesticide before rain",
    "what fertilizer should I use for my field",
    "how does humidity affect fungal disease",
    "where can I buy seeds and farm supplies nearby",
    "when should I harvest my crop",
    "how to control pests like aphids and mites organically",
]
OFF_TOPIC = [
    "write me a python program",
    "help me with my math homework",
    "write an essay about history",
    "who will win the election",
    "tell me a joke",
    "recommend a movie to watch",
    "what is the best smartphone to buy",
    "translate this sentence into French",
    "write a love poem",
    "explain how cryptocurrency works",
]
MIN_WORDS = 4


@lru_cache
def _anchor_embeddings():
    from app.services.knowledge_base import get_knowledge_base

    embed = get_knowledge_base().embed
    return embed(ON_TOPIC), embed(OFF_TOPIC)


def _max_similarity(vector: list[float], anchors: list[list[float]]) -> float:
    return max(sum(a * b for a, b in zip(vector, anchor)) for anchor in anchors)


def topic_scores_sync(text: str) -> tuple[float, float]:
    """(best on-topic similarity, best off-topic similarity)."""
    from app.services.knowledge_base import get_knowledge_base

    on_topic, off_topic = _anchor_embeddings()
    vector = get_knowledge_base().embed([text])[0]
    return _max_similarity(vector, on_topic), _max_similarity(vector, off_topic)


async def is_off_topic(text: str) -> bool:
    settings = get_settings()
    if not settings.topic_filter_enabled or len(text.split()) < MIN_WORDS:
        return False
    on_topic, off_topic = await asyncio.to_thread(topic_scores_sync, text)
    return off_topic - on_topic > settings.topic_filter_margin

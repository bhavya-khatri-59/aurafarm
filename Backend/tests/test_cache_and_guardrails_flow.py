"""Caching, demo mode and guardrails through the HTTP API. Paths that should not call the LLM use
models with no scripted responses, so any call fails the test."""

import chromadb
import groq
import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graph import build_graph
from app.db import session_factory
from app.main import app, load_image
from app.services import cache, classifier, guardrails, leaf_check, places, weather
from app.services.knowledge_base import KnowledgeBase
from tests.conftest import register
from tests.fakes import ScriptedChatModel, hashing_embedder, jpeg_bytes
from tests.test_agent_flow import parse_sse


@pytest.fixture(autouse=True)
def stubs(monkeypatch):
    async def predict(image_bytes, top_k=3):
        return [("Tomato___Late_blight", 0.93), ("Tomato___Early_blight", 0.04), ("Potato___Late_blight", 0.01)]

    async def no_weather(lat, lon):
        return None

    async def no_places(lat, lon, kind="all", limit=6):
        return []

    monkeypatch.setattr(classifier, "predict", predict)
    monkeypatch.setattr(weather, "get_weather", no_weather)
    monkeypatch.setattr(places, "find_nearby_places", no_places)


@pytest.fixture
def kb():
    client = chromadb.EphemeralClient()
    kb = KnowledgeBase(client, "cache_test", hashing_embedder)
    kb.upsert(
        ids=["lb1", "lb2"],
        documents=["Late blight: destroy infected plants.", "Late blight: apply mancozeb before rain."],
        metadatas=[{"crop": "tomato", "disease": "late_blight", "title": f"Guide {i}", "source_url": "", "source_org": "Ext"} for i in (1, 2)],
    )
    yield kb
    client.delete_collection("cache_test")


def use_graph(kb, orchestrator, remedy):
    app.state.graph = build_graph(orchestrator, remedy, lambda: kb, session_factory(), load_image, InMemorySaver())


async def start(client):
    headers = await register(client)
    conversation_id = (await client.post("/conversations", json={}, headers=headers)).json()["id"]
    return headers, conversation_id


async def upload(client, headers, data):
    return (await client.post("/uploads", files={"image": ("leaf.jpg", data, "image/jpeg")}, headers=headers)).json()["id"]


async def send(client, headers, conversation_id, **body):
    response = await client.post(f"/conversations/{conversation_id}/messages", json=body, headers=headers)
    return parse_sse(response.text)


def shown_text(events):
    text = ""
    for kind, data in events:
        text = "" if kind == "reset" else text + data["text"] if kind == "token" else text
    return text


async def test_same_photo_is_answered_from_cache_even_after_recompression(client, kb):
    orchestrator = ScriptedChatModel(responses=[AIMessage("Late blight. Destroy infected plants.")])
    remedy = ScriptedChatModel(responses=[AIMessage("Destroy infected plants.")])
    use_graph(kb, orchestrator, remedy)
    headers, first = await start(client)

    events = await send(client, headers, first, image_id=await upload(client, headers, jpeg_bytes(quality=95)))
    assert dict(events)["message"]["content"] == "Late blight. Destroy infected plants."

    # Same photo, re-compressed like the phone's picker does, in a new conversation: no LLM calls.
    second = (await client.post("/conversations", json={}, headers=headers)).json()["id"]
    events = await send(client, headers, second, image_id=await upload(client, headers, jpeg_bytes(quality=60)))
    assert dict(events)["diagnosis"]["label"] == "Tomato___Late_blight"
    assert shown_text(events) == "Late blight. Destroy infected plants."
    assert dict(events)["done"]["conversation_title"] == "Tomato late blight"
    assert len(orchestrator.calls) == 1 and len(remedy.calls) == 1

    # The cached turn is in the agent's state, so a follow-up has the diagnosis and history.
    orchestrator.responses.append(AIMessage("Yes."))
    await send(client, headers, second, text="Should I remove the plants?")
    follow_up = orchestrator.calls[-1]
    assert "Tomato late blight" in follow_up[0].content
    assert any(isinstance(m, AIMessage) and m.content.startswith("Late blight.") for m in follow_up)


async def test_different_text_with_same_photo_runs_the_agent_but_reuses_remedy_research(client, kb):
    orchestrator = ScriptedChatModel(responses=[AIMessage("First answer."), AIMessage("Organic answer.")])
    remedy = ScriptedChatModel(responses=[AIMessage("Destroy infected plants.")])
    use_graph(kb, orchestrator, remedy)
    headers, conversation_id = await start(client)

    await send(client, headers, conversation_id, image_id=await upload(client, headers, jpeg_bytes()))
    events = await send(
        client, headers, conversation_id, text="organic options only", image_id=await upload(client, headers, jpeg_bytes())
    )
    assert dict(events)["message"]["content"] == "Organic answer."
    assert len(remedy.calls) == 1  # research cached per disease


async def test_demo_mode_answers_only_cached_photos(client, kb):
    orchestrator = ScriptedChatModel(responses=[AIMessage("Late blight. Destroy infected plants.")])
    use_graph(kb, orchestrator, ScriptedChatModel(responses=[AIMessage("notes")]))
    headers, conversation_id = await start(client)
    await send(client, headers, conversation_id, image_id=await upload(client, headers, jpeg_bytes()))

    hit = await send(client, headers, conversation_id, demo_mode=True, text="what is this?",
                     image_id=await upload(client, headers, jpeg_bytes(quality=70)))
    assert shown_text(hit) == "Late blight. Destroy infected plants."

    miss = await send(client, headers, conversation_id, demo_mode=True,
                      image_id=await upload(client, headers, jpeg_bytes(color=(200, 30, 200), pattern=3)))
    assert "diagnosis" not in dict(miss)
    assert dict(miss)["message"]["content"] == guardrails.NOT_A_PLANT_REPLY
    assert len(orchestrator.calls) == 1


async def test_off_topic_text_is_refused_without_calling_the_llm(client, kb):
    use_graph(kb, ScriptedChatModel(responses=[]), ScriptedChatModel(responses=[]))
    headers, conversation_id = await start(client)
    events = await send(client, headers, conversation_id, text="Write a Python script to sort a list")
    assert dict(events)["message"]["content"] == guardrails.OFF_TOPIC_REPLY
    state = await app.state.graph.aget_state({"configurable": {"thread_id": conversation_id}})
    assert [type(m) for m in state.values["messages"]] == [HumanMessage, AIMessage]


async def test_code_in_a_reply_is_replaced(client, kb):
    use_graph(kb, ScriptedChatModel(responses=[AIMessage("Sure:\n```python\nprint(1)\n```")]), ScriptedChatModel(responses=[]))
    headers, conversation_id = await start(client)
    events = await send(client, headers, conversation_id, text="how do I water my tomatoes?")
    assert dict(events)["message"]["content"] == guardrails.OFF_TOPIC_REPLY
    state = await app.state.graph.aget_state({"configurable": {"thread_id": conversation_id}})
    assert state.values["messages"][-1].content == guardrails.OFF_TOPIC_REPLY


async def test_leaf_check_rejects_non_plant_photos(client, kb, monkeypatch):
    async def not_a_plant(image_bytes):
        return False

    monkeypatch.setattr(leaf_check, "looks_like_plant", not_a_plant)
    use_graph(kb, ScriptedChatModel(responses=[]), ScriptedChatModel(responses=[]))
    headers, conversation_id = await start(client)
    events = await send(client, headers, conversation_id, image_id=await upload(client, headers, jpeg_bytes()))
    assert "diagnosis" not in dict(events)
    assert dict(events)["message"]["content"] == guardrails.NOT_A_PLANT_REPLY


class RateLimitedModel(ScriptedChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        raise groq.RateLimitError("Too Many Requests", response=httpx.Response(429, request=request), body=None)


async def test_rate_limit_fails_fast_with_a_clear_message(client, kb):
    use_graph(kb, RateLimitedModel(responses=[]), ScriptedChatModel(responses=[]))
    headers, conversation_id = await start(client)
    events = await send(client, headers, conversation_id, text="how do I water my tomatoes?")
    assert dict(events)["error"]["detail"].startswith("The AI service is busy")


def test_perceptual_hash_tells_photos_apart():
    same = cache.hash_distance(cache.image_hash(jpeg_bytes(quality=95)), cache.image_hash(jpeg_bytes(quality=50)))
    different = cache.hash_distance(
        cache.image_hash(jpeg_bytes()), cache.image_hash(jpeg_bytes(color=(200, 30, 200), pattern=3))
    )
    assert same <= 2 and different > 10

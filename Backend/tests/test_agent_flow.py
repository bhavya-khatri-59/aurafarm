"""End-to-end agent turn through the HTTP API, with scripted LLMs and stubbed external services."""

import json

import chromadb
import pytest
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import select

from app.agents.graph import build_graph
from app.db import session_factory
from app.main import app, load_image
from app.models import DiseaseReport
from app.services import classifier, places, weather
from app.services.knowledge_base import KnowledgeBase
from tests.conftest import register
from tests.fakes import ScriptedChatModel, StreamingScriptedChatModel, hashing_embedder, tool_call


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


@pytest.fixture
def stub_services(monkeypatch):
    async def fake_predict(image_bytes, top_k=3):
        return [("Tomato___Late_blight", 0.91), ("Tomato___Early_blight", 0.05), ("Potato___Late_blight", 0.02)]

    async def fake_weather(lat, lon):
        return {"temp_c": 22, "humidity": 92, "condition": "Light rain", "forecast": []}

    async def fake_places(lat, lon, kind="all", limit=6):
        return [{"name": "Green Agro Inputs", "category": "Agri-input shop", "distance_km": 1.2}]

    monkeypatch.setattr(classifier, "predict", fake_predict)
    monkeypatch.setattr(weather, "get_weather", fake_weather)
    monkeypatch.setattr(places, "find_nearby_places", fake_places)


@pytest.fixture
def kb():
    client = chromadb.EphemeralClient()
    kb = KnowledgeBase(client, "flow_test", hashing_embedder)
    kb.upsert(
        ids=["lb", "eb"],
        documents=[
            "Late blight of tomato: destroy infected plants and apply mancozeb before rain.",
            "Early blight of tomato: remove lower leaves and apply chlorothalonil.",
        ],
        metadatas=[
            {"crop": "tomato", "disease": "late_blight", "title": "Late blight guide", "source_url": "https://ex.org/lb", "source_org": "Ext"},
            {"crop": "tomato", "disease": "early_blight", "title": "Early blight guide", "source_url": "https://ex.org/eb", "source_org": "Ext"},
        ],
    )
    yield kb
    client.delete_collection("flow_test")


async def test_photo_turn_then_follow_up(client, stub_services, kb):
    orchestrator = ScriptedChatModel(responses=[
        AIMessage("Your tomato has **late blight**. Apply mancozeb before the rain."),
        AIMessage("Yes, remove and destroy the infected plants."),
    ])
    remedy = ScriptedChatModel(responses=[
        tool_call("search_knowledge_base", {"query": "treat late blight"}),
        AIMessage("Destroy infected plants; apply mancozeb. Sources: Late blight guide (https://ex.org/lb)"),
    ])
    app.state.graph = build_graph(
        orchestrator_llm=orchestrator,
        remedy_llm=remedy,
        get_kb=lambda: kb,
        sessions=session_factory(),
        load_image=load_image,
        checkpointer=InMemorySaver(),
    )

    headers = await register(client)
    conversation_id = (await client.post("/conversations", json={}, headers=headers)).json()["id"]
    upload_id = (await client.post(
        "/uploads", files={"image": ("leaf.jpg", b"\xff\xd8fakejpeg", "image/jpeg")}, headers=headers
    )).json()["id"]

    # Turn 1: photo + location.
    response = await client.post(
        f"/conversations/{conversation_id}/messages",
        json={"text": "What is wrong with my plant?", "image_id": upload_id, "lat": 12.97, "lon": 77.59},
        headers=headers,
    )
    assert response.status_code == 200
    events = parse_sse(response.text)
    kinds = [kind for kind, _ in events]
    assert kinds[0] == "user_message" and kinds[-2:] == ["message", "done"]
    diagnosis = dict(events)["diagnosis"]
    assert diagnosis["status"] == "confident"
    assert diagnosis["name"] == "Tomato late blight"
    assert diagnosis["weather"]["humidity"] == 92
    assert diagnosis["nearby_places"][0]["name"] == "Green Agro Inputs"
    assert any(kind == "status" and "Researching" in data["text"] for kind, data in events)
    assert dict(events)["message"]["content"].startswith("Your tomato has **late blight**")
    assert dict(events)["done"]["conversation_title"] == "What is wrong with my plant?"

    # Remedy research ran deterministically after the diagnosis, scoped to the diagnosed disease,
    # and was asked about the current weather.
    assert "92% humidity" in remedy.calls[0][-1].content
    kb_result = next(m for m in remedy.calls[1] if isinstance(m, ToolMessage))
    hits = json.loads(kb_result.content)
    assert hits[0]["disease"] == "late_blight" and hits[0]["match"] == "crop_and_disease"

    # The orchestrator answered in one step with the diagnosis and the research in its context.
    assert len(orchestrator.calls) == 1
    system = orchestrator.calls[0][0]
    assert isinstance(system, SystemMessage) and "NEW this turn" in system.content
    assert "apply mancozeb. Sources: Late blight guide" in system.content
    assert "already been diagnosed" in orchestrator.calls[0][-1].content

    # A confident diagnosis with location is recorded for the community outbreak signal.
    async with session_factory()() as session:
        reports = (await session.scalars(select(DiseaseReport))).all()
    assert len(reports) == 1 and reports[0].lat == 12.97

    # Turn 2: a follow-up without a photo keeps the diagnosis and the research from checkpointed state.
    response = await client.post(
        f"/conversations/{conversation_id}/messages", json={"text": "Should I remove the plants?"}, headers=headers
    )
    events = parse_sse(response.text)
    assert "diagnosis" not in [kind for kind, _ in events]
    assert dict(events)["message"]["content"] == "Yes, remove and destroy the infected plants."
    follow_up_system = orchestrator.calls[1][0].content
    assert "from an earlier message" in follow_up_system and "Tomato___Late_blight" in follow_up_system
    assert "apply mancozeb. Sources: Late blight guide" in follow_up_system
    assert len(remedy.calls) == 2  # no new research needed

    detail = (await client.get(f"/conversations/{conversation_id}", headers=headers)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]
    assert detail["messages"][0]["image_id"] == upload_id
    assert detail["messages"][1]["diagnosis"]["label"] == "Tomato___Late_blight"


async def test_text_streamed_before_a_tool_call_is_reset(client, kb, monkeypatch):
    from app.services import web_search as web_search_module

    async def no_results(query, max_results=5):
        return []

    monkeypatch.setattr(web_search_module, "web_search", no_results)
    orchestrator = StreamingScriptedChatModel(responses=[
        AIMessage("Let me look that up.", tool_calls=[
            {"name": "consult_remedy_specialist", "args": {"question": "aphids on tomato?"}, "id": "c1", "type": "tool_call"}
        ]),
        AIMessage("Spray insecticidal soap."),
    ])
    app.state.graph = build_graph(
        orchestrator, ScriptedChatModel(responses=[AIMessage("Use insecticidal soap.")]),
        lambda: kb, session_factory(), load_image, InMemorySaver(),
    )
    headers = await register(client)
    conversation_id = (await client.post("/conversations", json={}, headers=headers)).json()["id"]
    events = parse_sse((await client.post(
        f"/conversations/{conversation_id}/messages", json={"text": "aphids?"}, headers=headers
    )).text)

    # Replaying the stream the way the app does gives only the final answer.
    shown = ""
    for kind, data in events:
        if kind == "reset":
            shown = ""
        elif kind == "token":
            shown += data["text"]
    assert "reset" in [kind for kind, _ in events]
    assert shown == "Spray insecticidal soap."
    assert dict(events)["message"]["content"] == "Spray insecticidal soap."


async def test_uncertain_diagnosis_is_not_recorded(client, monkeypatch, stub_services, kb):
    async def unsure(image_bytes, top_k=3):
        return [("Tomato___Late_blight", 0.35), ("Tomato___Early_blight", 0.30), ("Potato___Late_blight", 0.2)]

    monkeypatch.setattr(classifier, "predict", unsure)
    orchestrator = ScriptedChatModel(responses=[AIMessage("I'm not sure. Could you send a clearer photo?")])
    app.state.graph = build_graph(
        orchestrator, ScriptedChatModel(responses=[]), lambda: kb, session_factory(), load_image, InMemorySaver()
    )
    headers = await register(client)
    conversation_id = (await client.post("/conversations", json={}, headers=headers)).json()["id"]
    upload_id = (await client.post(
        "/uploads", files={"image": ("leaf.jpg", b"\xff\xd8fakejpeg", "image/jpeg")}, headers=headers
    )).json()["id"]

    events = parse_sse((await client.post(
        f"/conversations/{conversation_id}/messages",
        json={"image_id": upload_id, "lat": 12.97, "lon": 77.59},
        headers=headers,
    )).text)
    diagnosis = dict(events)["diagnosis"]
    assert diagnosis["status"] == "uncertain"
    assert diagnosis["nearby_places"] is None
    assert len(diagnosis["alternatives"]) == 2
    assert dict(events)["done"]["conversation_title"] == "Plant diagnosis"
    async with session_factory()() as session:
        assert (await session.scalars(select(DiseaseReport))).all() == []

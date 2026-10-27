"""Groq rejects malformed tool calls server-side; one bad call must not fail the farmer's turn."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.graph import build_graph
from app.agents.remedy import build_remedy_agent, run_remedy_agent
from app.db import session_factory
from tests.fakes import AlwaysFailingChatModel, FailingOnceChatModel, ScriptedChatModel, tool_call


class CapturingModel(ScriptedChatModel):
    tools: list = []

    def bind_tools(self, tools, **kwargs):
        self.tools.extend(convert_to_openai_tool(t) for t in tools)
        return self


async def _no_image(image_id: str) -> bytes:
    raise AssertionError("no image expected")


async def test_tool_schemas_have_no_required_arguments(db):
    """Required args let Groq fail the whole request when a model omits one."""
    orchestrator, remedy = CapturingModel(responses=[]), CapturingModel(responses=[])
    build_graph(orchestrator, remedy, lambda: None, session_factory(), _no_image)
    for spec in orchestrator.tools + remedy.tools:
        assert not spec["function"]["parameters"].get("required"), spec["function"]["name"]
        assert "state" not in spec["function"]["parameters"]["properties"]


class FakeKB:
    def __init__(self, hits):
        self.hits = hits
        self.searches = []

    async def asearch(self, query, crop=None, disease=None, k=5):
        self.searches.append((query, crop, disease))
        return self.hits


SCOPED_HIT = {"text": "Apply mancozeb.", "title": "Guide", "source_url": "https://ex.org", "match": "crop_and_disease"}


async def test_remedy_agent_retries_after_groq_error():
    remedy = FailingOnceChatModel(responses=[AIMessage("Use mancozeb.")])
    agent = build_remedy_agent(remedy, lambda: FakeKB([SCOPED_HIT, SCOPED_HIT]))
    assert await run_remedy_agent(agent, "late blight?", "tomato", "late_blight") == "Use mancozeb."


async def test_remedy_agent_uses_web_only_when_knowledge_base_is_thin(monkeypatch):
    from app.agents import remedy as remedy_module

    queries = []

    async def fake_web_search(query, max_results=5):
        queries.append(query)
        return [{"title": "Web page", "url": "https://web.example", "snippet": "Spray copper."}]

    monkeypatch.setattr(remedy_module, "web_search", fake_web_search)

    model = ScriptedChatModel(responses=[AIMessage("notes 1"), AIMessage("notes 2")])
    agent = build_remedy_agent(model, lambda: FakeKB([SCOPED_HIT, SCOPED_HIT]))
    await run_remedy_agent(agent, "treat it?", "tomato", "late_blight")
    assert queries == []

    agent = build_remedy_agent(model, lambda: FakeKB([{**SCOPED_HIT, "match": "unscoped"}]))
    await run_remedy_agent(agent, "treat it?", "tomato", "late_blight")
    assert queries == ["tomato late blight treat it?"]
    assert "[WEB1] Web page (https://web.example)" in model.calls[1][-1].content
    assert len(model.calls) == 2  # still one LLM call per question


async def test_turn_completes_when_remedy_agent_fails(db):
    orchestrator = ScriptedChatModel(responses=[
        tool_call("consult_remedy_specialist", {"question": "treat blight?"}),
        AIMessage("I couldn't check sources, but here is general advice."),
    ])
    graph = build_graph(
        orchestrator, AlwaysFailingChatModel(responses=[]), lambda: None, session_factory(), _no_image,
        InMemorySaver(),
    )
    result = await graph.ainvoke(
        {"messages": [HumanMessage("my tomato has blight")], "user_id": 1, "new_diagnosis": False},
        {"configurable": {"thread_id": "t"}},
    )
    assert result["messages"][-1].content.startswith("I couldn't check sources")
    tool_result = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert "unavailable" in tool_result.content

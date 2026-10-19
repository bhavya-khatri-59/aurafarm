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


async def test_remedy_agent_retries_after_groq_tool_call_error():
    remedy = FailingOnceChatModel(responses=[AIMessage("Use mancozeb.")])
    agent = build_remedy_agent(remedy, lambda: None)
    assert await run_remedy_agent(agent, "late blight?", "tomato", "late_blight") == "Use mancozeb."


async def test_empty_web_search_call_gets_an_error_message_not_a_crash():
    remedy = ScriptedChatModel(responses=[tool_call("search_web", {}), AIMessage("done")])
    agent = build_remedy_agent(remedy, lambda: None)
    await run_remedy_agent(agent, "q", None, None)
    tool_result = next(m for m in remedy.calls[1] if isinstance(m, ToolMessage))
    assert "non-empty" in tool_result.content


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

"""The AuraFarm agent graph.

    START ─┬─(photo)─> diagnose ─┬─(confident disease)─> remedy_research ─┐
           │                     └────────────────────────────────────────┤
           └──────────────────────────────────────────────────────────────┴─> orchestrator <──> tools ─> END

- diagnose: deterministic node (classifier, weather, outbreaks, places).
- remedy_research: runs the remedy agent for a new confident diagnosis, so treatment advice never
  depends on the orchestrator deciding to ask for it.
- orchestrator: LLM that talks to the farmer and decides which tools/agents to call.
- tools: `consult_remedy_specialist` (the remedy agent, for other questions) and `find_nearby_help`.
"""

import json
import logging
from collections.abc import Callable
from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, trim_messages
from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.tools import tool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.config import get_stream_writer
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import InjectedState, ToolNode, tools_condition
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents.diagnosis import ImageLoader, make_diagnosis_node
from app.agents.llm import retry_on_groq_error
from app.agents.prompts import ORCHESTRATOR_PROMPT
from app.agents.remedy import build_remedy_agent, run_remedy_agent
from app.agents.state import AgentState
from app.config import get_settings
from app.services import places
from app.services.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

ORCHESTRATOR_NODE = "orchestrator"


def _context_block(state: AgentState) -> str:
    diagnosis = state.get("diagnosis")
    parts = [
        "Farmer location: " + ("shared" if state.get("location") else "not shared"),
    ]
    if diagnosis is None:
        parts.append("No photo has been diagnosed in this conversation yet.")
    else:
        freshness = (
            "NEW this turn: the photo has already been analysed, present this result now"
            if state.get("new_diagnosis") else "from an earlier message"
        )
        parts.append(f"Latest photo diagnosis ({freshness}):\n{json.dumps(diagnosis)}")
    if state.get("remedy_notes"):
        parts.append(f"Remedy specialist's research for this diagnosis (already done):\n{state['remedy_notes']}")
    return "\n\n".join(parts)


def _remedy_question(diagnosis: dict) -> str:
    question = f"How should a farmer treat and prevent {diagnosis['name'].lower()}?"
    weather = diagnosis.get("weather") or {}
    if weather.get("humidity") is not None:
        question += (
            f" Current weather: {weather.get('condition')}, {weather.get('temp_c')}°C, "
            f"{weather.get('humidity')}% humidity. Include cultural/organic and chemical options."
        )
    return question


def build_graph(
    orchestrator_llm: BaseChatModel,
    remedy_llm: BaseChatModel,
    get_kb: Callable[[], KnowledgeBase],
    sessions: async_sessionmaker[AsyncSession],
    load_image: ImageLoader,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    remedy_agent = build_remedy_agent(remedy_llm, get_kb)

    async def research(question: str, diagnosis: dict) -> str:
        get_stream_writer()({"type": "status", "text": "Researching treatments…"})
        confident = diagnosis.get("status") == "confident"
        try:
            return await run_remedy_agent(
                remedy_agent,
                question,
                crop=diagnosis.get("crop") if confident else None,
                disease=diagnosis.get("disease") if confident else None,
            )
        except GraphRecursionError:
            return "The remedy specialist could not finish its research. Answer from general knowledge with caution."
        except Exception:
            logger.exception("Remedy agent failed")
            return (
                "The remedy specialist is unavailable right now. Answer from general knowledge with "
                "caution, say that sources could not be checked, and suggest local extension services."
            )

    async def remedy_research(state: AgentState) -> dict:
        diagnosis = state["diagnosis"]
        return {"remedy_notes": await research(_remedy_question(diagnosis), diagnosis)}

    @tool
    async def consult_remedy_specialist(
        state: Annotated[dict, InjectedState], question: str = ""
    ) -> str:
        """Ask the remedy specialist about treatment, prevention, products, spraying or disease
        biology. It researches curated extension guides and the web and returns cited advice.

        Args:
            question: A self-contained question including the crop, the disease and any relevant
                details from the conversation (weather, organic preference, severity, region).
        """
        diagnosis = state.get("diagnosis") or {}
        if not question.strip():
            if not diagnosis:
                return "Error: pass the farmer's question as `question`."
            question = _remedy_question(diagnosis)
        return await research(question, diagnosis)

    @tool
    async def find_nearby_help(
        state: Annotated[dict, InjectedState], kind: str = "all"
    ) -> str:
        """Find places near the farmer to buy farm inputs or get expert agricultural help.

        Args:
            kind: "agri_supplies" (input/seed/pesticide shops), "expert_help" (agriculture
                offices, Krishi Vigyan Kendras, research stations) or "all".
        """
        location = state.get("location")
        if not location:
            return "The farmer has not shared their location. Ask them to enable location sharing."
        get_stream_writer()({"type": "status", "text": "Looking for help nearby…"})
        if kind not in {"agri_supplies", "expert_help"}:
            kind = "all"
        found = await places.find_nearby_places(location["lat"], location["lon"], kind=kind, limit=8)
        if not found:
            return "No matching places were found nearby in OpenStreetMap."
        return json.dumps(found, ensure_ascii=False)

    tools = [consult_remedy_specialist, find_nearby_help]
    llm_with_tools = retry_on_groq_error(orchestrator_llm.bind_tools(tools))

    async def orchestrator(state: AgentState) -> dict:
        history = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=count_tokens_approximately,
            max_tokens=get_settings().max_history_tokens,
            start_on="human",
        )
        system = SystemMessage(ORCHESTRATOR_PROMPT.format(context=_context_block(state)))
        return {"messages": [await llm_with_tools.ainvoke([system, *history])]}

    def route_start(state: AgentState) -> str:
        return "diagnose" if state.get("image_id") else ORCHESTRATOR_NODE

    def route_after_diagnosis(state: AgentState) -> str:
        diagnosis = state["diagnosis"]
        if diagnosis["status"] == "confident" and not diagnosis["is_healthy"]:
            return "remedy_research"
        return ORCHESTRATOR_NODE

    graph = StateGraph(AgentState)
    graph.add_node("diagnose", make_diagnosis_node(sessions, load_image))
    graph.add_node("remedy_research", remedy_research)
    graph.add_node(ORCHESTRATOR_NODE, orchestrator)
    graph.add_node("tools", ToolNode(tools))
    graph.add_conditional_edges(START, route_start, ["diagnose", ORCHESTRATOR_NODE])
    graph.add_conditional_edges("diagnose", route_after_diagnosis, ["remedy_research", ORCHESTRATOR_NODE])
    graph.add_edge("remedy_research", ORCHESTRATOR_NODE)
    graph.add_conditional_edges(ORCHESTRATOR_NODE, tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", ORCHESTRATOR_NODE)
    return graph.compile(checkpointer=checkpointer, name="aurafarm")

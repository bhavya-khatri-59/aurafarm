"""The AuraFarm agent graph.

    START ─┬─(photo attached)─> diagnose ─> orchestrator <──> tools ─> END
           └──────────────────────────────> orchestrator

- diagnose: deterministic node (classifier, weather, outbreaks, places).
- orchestrator: LLM that talks to the farmer and decides which tools/agents to call.
- tools: includes `consult_remedy_specialist`, which runs the remedy agent (its own graph).
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
        freshness = "NEW this turn" if state.get("new_diagnosis") else "from an earlier message"
        parts.append(f"Latest photo diagnosis ({freshness}):\n{json.dumps(diagnosis, indent=1)}")
    return "\n".join(parts)


def build_graph(
    orchestrator_llm: BaseChatModel,
    remedy_llm: BaseChatModel,
    get_kb: Callable[[], KnowledgeBase],
    sessions: async_sessionmaker[AsyncSession],
    load_image: ImageLoader,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    remedy_agent = build_remedy_agent(remedy_llm, get_kb)

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
        get_stream_writer()({"type": "status", "text": "Researching treatments…"})
        diagnosis = state.get("diagnosis") or {}
        confident = diagnosis.get("status") == "confident"
        if not question.strip():
            if not diagnosis:
                return "Error: pass the farmer's question as `question`."
            question = f"How should a farmer treat and prevent {diagnosis['name'].lower()}?"
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

    graph = StateGraph(AgentState)
    graph.add_node("diagnose", make_diagnosis_node(sessions, load_image))
    graph.add_node(ORCHESTRATOR_NODE, orchestrator)
    graph.add_node("tools", ToolNode(tools))
    graph.add_conditional_edges(START, route_start, ["diagnose", ORCHESTRATOR_NODE])
    graph.add_edge("diagnose", ORCHESTRATOR_NODE)
    graph.add_conditional_edges(ORCHESTRATOR_NODE, tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", ORCHESTRATOR_NODE)
    return graph.compile(checkpointer=checkpointer, name="aurafarm")

"""The AuraFarm agent graph.

    START ─┬─(photo)─> diagnose ─┬─(not a plant)──────────> reject_image ─> END
           │                     ├─(confident disease)─> remedy_research ─┐
           │                     └────────────────────────────────────────┤
           └──────────────────────────────────────────────────────────────┴─> orchestrator <──> tools ─> END

- diagnose: deterministic node (optional leaf check, classifier, weather, outbreaks, places).
- reject_image: fixed reply for photos that fail the leaf check; no LLM call.
- remedy_research: runs the remedy agent for a new confident diagnosis, so treatment advice never
  depends on the orchestrator deciding to ask for it. Research is cached per disease.
- orchestrator: LLM that talks to the farmer and decides which tools/agents to call.
- tools: `consult_remedy_specialist` (the remedy agent, for other questions) and `find_nearby_help`.
"""

import json
import logging
from collections.abc import Callable
from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, trim_messages
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
from app.services import cache, places
from app.services.guardrails import NOT_A_PLANT_REPLY
from app.services.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

ORCHESTRATOR_NODE = "orchestrator"


def _compact_diagnosis(diagnosis: dict) -> dict:
    """The diagnosis without fields the LLM doesn't need, to keep prompts (and token use) small."""
    compact = {k: v for k, v in diagnosis.items() if k not in {"label", "crop", "disease", "location_available"}}
    if compact.get("weather") and compact["weather"].get("forecast"):
        compact["weather"] = {
            **compact["weather"],
            "forecast": [
                {k: day.get(k) for k in ("date", "chance_of_rain", "avg_humidity", "condition")}
                for day in compact["weather"]["forecast"]
            ],
        }
    if compact.get("nearby_places"):
        compact["nearby_places"] = [
            {k: place.get(k) for k in ("name", "category", "distance_km")} for place in compact["nearby_places"][:4]
        ]
    return compact


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
        parts.append(f"Latest photo diagnosis ({freshness}):\n{json.dumps(_compact_diagnosis(diagnosis))}")
    if state.get("remedy_notes"):
        parts.append(f"Remedy specialist's research for this diagnosis (already done):\n{state['remedy_notes']}")
    return "\n\n".join(parts)


def _remedy_question(diagnosis: dict) -> str:
    # Weather-independent so the research can be cached per disease; the orchestrator relates it
    # to the current weather.
    return (
        f"How should a farmer treat and prevent {diagnosis['name'].lower()}? "
        "Include cultural/organic and chemical options, and how weather affects the disease."
    )


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
        async with sessions() as session:
            notes = await cache.get_remedy_notes(session, diagnosis["label"])
        if notes is None:
            notes = await research(_remedy_question(diagnosis), diagnosis)
            if not notes.startswith("The remedy specialist"):  # don't cache failure fallbacks
                async with sessions() as session:
                    await cache.store_remedy_notes(session, diagnosis["label"], notes)
        return {"remedy_notes": notes}

    async def reject_image(state: AgentState) -> dict:
        return {"messages": [AIMessage(NOT_A_PLANT_REPLY)]}

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
        if state.get("image_rejected"):
            return "reject_image"
        diagnosis = state["diagnosis"]
        if diagnosis["status"] == "confident" and not diagnosis["is_healthy"]:
            return "remedy_research"
        return ORCHESTRATOR_NODE

    graph = StateGraph(AgentState)
    graph.add_node("diagnose", make_diagnosis_node(sessions, load_image))
    graph.add_node("remedy_research", remedy_research)
    graph.add_node("reject_image", reject_image)
    graph.add_node(ORCHESTRATOR_NODE, orchestrator)
    graph.add_node("tools", ToolNode(tools))
    graph.add_conditional_edges(START, route_start, ["diagnose", ORCHESTRATOR_NODE])
    graph.add_conditional_edges(
        "diagnose", route_after_diagnosis, ["reject_image", "remedy_research", ORCHESTRATOR_NODE]
    )
    graph.add_edge("reject_image", END)
    graph.add_edge("remedy_research", ORCHESTRATOR_NODE)
    graph.add_conditional_edges(ORCHESTRATOR_NODE, tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", ORCHESTRATOR_NODE)
    return graph.compile(checkpointer=checkpointer, name="aurafarm")

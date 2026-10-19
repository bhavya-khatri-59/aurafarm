"""Remedy recommendation agent: a tool-calling loop over the knowledge base and the web."""

import json
from collections.abc import Callable
from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import InjectedState, ToolNode, tools_condition

from app.agents.llm import retry_on_groq_error
from app.agents.prompts import REMEDY_PROMPT
from app.services.knowledge_base import KnowledgeBase
from app.services.labels import CROPS, DISEASES
from app.services.web_search import web_search

MAX_STEPS = 12


class RemedyState(MessagesState):
    crop: str | None
    disease: str | None


def build_remedy_agent(llm: BaseChatModel, get_kb: Callable[[], KnowledgeBase]) -> CompiledStateGraph:
    """get_kb returns the KnowledgeBase lazily, so the embedding model only loads when needed."""

    @tool
    async def search_knowledge_base(
        state: Annotated[dict, InjectedState],
        query: str = "",
        crop: str | None = None,
        disease: str | None = None,
    ) -> str:
        """Search curated extension guides on plant diseases and treatments.

        Args:
            query: What to look for, e.g. "organic treatment for early blight".
            crop: Crop slug to scope the search to. Defaults to the diagnosed crop.
            disease: Disease slug to scope the search to. Defaults to the diagnosed disease.
        """
        crop = crop if crop in CROPS else state.get("crop")
        disease = disease if disease in DISEASES else state.get("disease")
        query = query.strip() or " ".join(p for p in (crop, disease, "treatment") if p).replace("_", " ")
        hits = await get_kb().asearch(query, crop=crop, disease=disease, k=5)
        if not hits:
            return "No relevant knowledge base material found."
        return json.dumps(hits, ensure_ascii=False)

    @tool
    async def search_web(query: str = "") -> str:
        """Search the web for up-to-date or region-specific agricultural information.

        Args:
            query: The search query. Include the crop, the disease and, if relevant, the region.
        """
        if not query.strip():
            return "Error: pass a non-empty `query`."
        results = await web_search(query)
        if not results:
            return "Web search returned no results."
        return json.dumps(results, ensure_ascii=False)

    tools = [search_knowledge_base, search_web]
    llm_with_tools = retry_on_groq_error(llm.bind_tools(tools))

    async def call_model(state: RemedyState):
        diagnosis = (
            f"crop={state.get('crop')}, disease={state.get('disease')}" if state.get("crop") else "none"
        )
        messages = [SystemMessage(REMEDY_PROMPT.format(diagnosis=diagnosis)), *state["messages"]]
        return {"messages": [await llm_with_tools.ainvoke(messages)]}

    graph = StateGraph(RemedyState)
    graph.add_node("remedy_llm", call_model)
    graph.add_node("remedy_tools", ToolNode(tools))
    graph.add_edge(START, "remedy_llm")
    graph.add_conditional_edges("remedy_llm", tools_condition, {"tools": "remedy_tools", END: END})
    graph.add_edge("remedy_tools", "remedy_llm")
    return graph.compile(name="remedy_agent")


async def run_remedy_agent(
    agent: CompiledStateGraph, question: str, crop: str | None, disease: str | None
) -> str:
    result = await agent.ainvoke(
        {"messages": [HumanMessage(question)], "crop": crop, "disease": disease},
        config={"recursion_limit": MAX_STEPS},
    )
    return result["messages"][-1].content

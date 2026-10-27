"""Remedy recommendation agent: retrieval-augmented generation over the knowledge base.

    START -> retrieve -(knowledge base thin)-> search_web -> summarize -> END
                     └──────────────────────────────────────> summarize

Retrieval is deterministic, so the agent makes exactly one LLM call (rate limits are the
bottleneck on the free LLM tier, not reasoning depth).
"""

import json
from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from typing_extensions import TypedDict

from app.agents.llm import retry_on_groq_error
from app.agents.prompts import REMEDY_PROMPT
from app.services.knowledge_base import KnowledgeBase
from app.services.web_search import web_search

KB_RESULTS = 5
# Fewer scoped hits than this sends the agent to the web as well.
MIN_SCOPED_HITS = 2
MAX_CHUNK_CHARS = 700
MAX_SNIPPET_CHARS = 300


class RemedyState(TypedDict, total=False):
    question: str
    crop: str | None
    disease: str | None
    kb_hits: list[dict]
    web_results: list[dict]
    notes: str


def _format_sources(state: RemedyState) -> str:
    parts = []
    for i, hit in enumerate(state.get("kb_hits") or [], 1):
        source = hit.get("source_url") or hit.get("source_org") or "AuraFarm notes"
        parts.append(f"[KB{i}] {hit.get('title')} ({source})\n{hit['text'][:MAX_CHUNK_CHARS]}")
    for i, result in enumerate(state.get("web_results") or [], 1):
        parts.append(f"[WEB{i}] {result.get('title')} ({result.get('url')})\n{result.get('snippet', '')[:MAX_SNIPPET_CHARS]}")
    return "\n\n".join(parts) or "No sources were found."


def build_remedy_agent(llm: BaseChatModel, get_kb: Callable[[], KnowledgeBase]) -> CompiledStateGraph:
    """get_kb returns the KnowledgeBase lazily, so the embedding model only loads when needed."""
    summarizer = retry_on_groq_error(llm)

    async def retrieve(state: RemedyState) -> dict:
        hits = await get_kb().asearch(state["question"], crop=state.get("crop"), disease=state.get("disease"), k=KB_RESULTS)
        return {"kb_hits": hits}

    def needs_web(state: RemedyState) -> str:
        scoped = [h for h in state.get("kb_hits") or [] if h.get("match") != "unscoped"]
        return "search_web" if len(scoped) < MIN_SCOPED_HITS else "summarize"

    async def search_web(state: RemedyState) -> dict:
        topic = " ".join(p for p in (state.get("crop"), state.get("disease")) if p).replace("_", " ")
        query = f"{topic} {state['question']}".strip() if topic else state["question"]
        return {"web_results": await web_search(query, max_results=4)}

    async def summarize(state: RemedyState) -> dict:
        diagnosis = f"crop={state.get('crop')}, disease={state.get('disease')}" if state.get("crop") else "none"
        messages = [
            SystemMessage(REMEDY_PROMPT.format(diagnosis=diagnosis)),
            HumanMessage(f"Question: {state['question']}\n\nSources:\n{_format_sources(state)}"),
        ]
        response = await summarizer.ainvoke(messages)
        return {"notes": response.content if isinstance(response.content, str) else json.dumps(response.content)}

    graph = StateGraph(RemedyState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("search_web", search_web)
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "retrieve")
    graph.add_conditional_edges("retrieve", needs_web, ["search_web", "summarize"])
    graph.add_edge("search_web", "summarize")
    graph.add_edge("summarize", END)
    return graph.compile(name="remedy_agent")


async def run_remedy_agent(
    agent: CompiledStateGraph, question: str, crop: str | None, disease: str | None
) -> str:
    result = await agent.ainvoke({"question": question, "crop": crop, "disease": disease})
    return result["notes"]

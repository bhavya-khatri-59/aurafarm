from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class Location(TypedDict):
    lat: float
    lon: float


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: int
    # Set only on turns where the user attached a photo; the diagnosis node consumes and clears it.
    image_id: str | None
    location: Location | None
    # The most recent diagnosis in this conversation; persists across turns for follow-up questions.
    diagnosis: dict | None
    new_diagnosis: bool

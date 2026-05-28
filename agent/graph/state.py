from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

REQUIRED_FIELDS: tuple[str, ...] = (
    'name',
    'depth',
    'location',
    'start_date',
)


class CollectedData(TypedDict, total=False):
    name: str | None
    depth: str | None
    location : str | None
    start_date: str | None


class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]
    collected_data: CollectedData
    is_complete: bool

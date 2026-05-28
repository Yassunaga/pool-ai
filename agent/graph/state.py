from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages

REQUIRED_FIELDS: tuple[str, ...] = (
    'location',
    'depth',
    'purpose',
    'flow_rate',
    'terrain',
)


class CollectedData(TypedDict, total=False):
    location: str | None
    depth: str | None
    purpose: str | None
    flow_rate: str | None
    terrain: str | None


class ConversationState(TypedDict):
    messages: Annotated[list, add_messages]
    collected_data: CollectedData
    is_complete: bool

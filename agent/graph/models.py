from typing import Annotated, TypedDict
from pydantic import BaseModel, Field

from langgraph.graph.message import add_messages

REQUIRED_FIELDS: tuple[str, ...] = (
    'location',
    'depth',
    'purpose',
)

FIELD_LABELS: dict[str, str] = {
    'location': 'cidade ou localização',
    'depth': 'profundidade estimada',
    'purpose': 'finalidade do poço',
}


class CollectedData(TypedDict, total=False):
    location: str | None
    location_type: str | None
    depth: str | None
    purpose: str | None
    flow_rate: str | None
    terrain: str | None


class ConversationState(TypedDict):
    is_greeted: bool
    messages: Annotated[list, add_messages]
    collected_data: CollectedData
    workflow_step: str

class WorkflowClassification(BaseModel):
    is_answer: bool
    captured_value: str | None = Field(None)
    reply_messages: list[str]


class ExtractedData(BaseModel):
    location: str | None = Field(None, description='cidade ou localização do poço')
    depth: str | None = Field(None, description='profundidade estimada do poço')
    purpose: str | None = Field(None, description='finalidade do poço')
    flow_rate: str | None = Field(None, description='vazão desejada')
    terrain: str | None = Field(None, description='tipo de terreno')

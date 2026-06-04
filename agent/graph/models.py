from typing import Annotated, Literal

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class Lead(BaseModel):
    """Dados coletados do lead. Hoje: nome e tipo de área."""

    name: str | None = None
    area_type: Literal['urban', 'rural'] | None = None


class ConversationState(BaseModel):
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    lead: Lead = Field(default_factory=Lead)

from typing import Annotated

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class ConversationState(BaseModel):
    messages: Annotated[list, add_messages] = Field(default_factory=list)

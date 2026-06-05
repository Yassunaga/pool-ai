from typing import Annotated, Literal

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class Lead(BaseModel):
    """Dados coletados do lead. Hoje: nome e tipo de área."""

    name: str | None = None
    area_type: Literal['urban', 'rural'] | None = None


class ChunkedReply(BaseModel):
    """Resposta do atendente dividida em mensagens curtas, para enviar
    separadamente no WhatsApp (como uma pessoa digitando em sequência)."""

    chunks: list[str] = Field(
        description='1 a 3 mensagens curtas, na ordem de envio, para mandar '
        'separadamente no WhatsApp. Quebre em pontos naturais (por frase ou '
        'ideia); se a resposta for curta, use uma única mensagem.',
        min_length=1,
        max_length=3,
    )


class ConversationState(BaseModel):
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    lead: Lead = Field(default_factory=Lead)

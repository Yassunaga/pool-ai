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
    request_handoff: bool = Field(
        default=False,
        description='True se NESTA mensagem o cliente pediu ou aceitou ser '
        'encaminhado para um atendente humano/especialista, ou se você '
        'confirmou o encaminhamento. False caso contrário.',
    )


class ConversationState(BaseModel):
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    lead: Lead = Field(default_factory=Lead)
    # Vira True quando o cliente pede/aceita falar com um humano; é "pegajoso"
    # (não volta a False) e dispara a notificação ao time uma única vez.
    handoff_requested: bool = False
    # Vira True no turno em que a tool `build_budget` informa o valor médio; é
    # "pegajoso" (não volta a False). Garante por estado — não por prompt — que o
    # valor seja citado uma única vez na conversa: a tool passa a recusar repetir.
    budget_given: bool = False

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from langgraph.graph.message import add_messages

from agent.graph.reducers import append_skill


AreaType = Literal['urbano', 'rural']

LeadStage = Literal['novo', 'qualificando', 'qualificado', 'agendado', 'perdido']

Intent = Literal[
    'greet',
    'ask_area',
    'urban_flow',
    'rural_flow',
    'faq',
    'pricing',
    'schedule',
    'handoff',
    'close',
]


REQUIRED_FIELDS: tuple[str, ...] = ('area_type',)

FIELD_LABELS: dict[str, str] = {
    'area_type': 'tipo de área (urbano ou rural)',
}


class CollectedData(BaseModel):
    """Dados estruturados do lead, extraídos da conversa.

    Nesta fase do produto coletamos apenas `area_type` — todo o resto da
    conversa diverge a partir desse dado.
    """

    area_type: AreaType | None = Field(
        None,
        description='tipo de área do poço: "urbano" (cidade, bairro, condomínio) ou "rural" (sítio, fazenda, chácara, propriedade rural)',
    )


class ConversationState(BaseModel):
    """Estado completo de uma conversa do agente, persistido pelo checkpointer."""

    is_greeted: bool = False
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    collected_data: CollectedData = Field(default_factory=CollectedData)

    # supervisor / skills
    intent: Intent | None = None
    confidence_last_route: float | None = None
    lead_stage: LeadStage = 'novo'
    skill_path: Annotated[list[str], append_skill] = Field(default_factory=list)
    turn_count: int = 0


class SupervisorRoute(BaseModel):
    """Decisão de roteamento do supervisor."""

    skill: Intent = Field(description='qual skill deve atender o cliente agora')
    reasoning: str = Field(description='justificativa curta da decisão (1 frase)')
    confidence: float = Field(
        description='certeza do roteamento de 0.0 a 1.0',
        ge=0.0,
        le=1.0,
    )


class GreetResponse(BaseModel):
    """Saudação inicial dividida em mensagens curtas para WhatsApp."""

    chunks: list[str] = Field(
        description='2 ou 3 mensagens curtas para enviar separadamente no WhatsApp',
        min_length=2,
        max_length=3,
    )


class FaqResponse(BaseModel):
    """Resposta a uma dúvida do cliente, dividida em mensagens curtas."""

    chunks: list[str] = Field(
        description='1 a 3 mensagens curtas respondendo à dúvida do cliente',
        min_length=1,
        max_length=3,
    )

from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from langgraph.graph.message import add_messages

from agent.graph.reducers import append_skill

LeadStage = Literal['novo', 'qualificando', 'qualificado', 'agendado', 'perdido']
Intent = Literal['greet', 'qualify', 'faq', 'pricing', 'schedule', 'handoff', 'close']


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


class CollectedData(BaseModel):
    """Dados estruturados do lead, extraídos da conversa ao longo do tempo."""

    location: str | None = Field(None, description='cidade ou localização do poço')
    depth: str | None = Field(None, description='profundidade estimada do poço')
    purpose: str | None = Field(None, description='finalidade do poço')
    flow_rate: str | None = Field(None, description='vazão desejada')
    terrain: str | None = Field(None, description='tipo de terreno')


class ConversationState(BaseModel):
    """Estado completo de uma conversa do agente, persistido pelo checkpointer."""

    is_greeted: bool = False
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    collected_data: CollectedData = Field(default_factory=CollectedData)
    workflow_step: str | None = None

    # supervisor / skills
    intent: Intent | None = None
    confidence_last_route: float | None = None
    lead_stage: LeadStage = 'novo'
    skill_path: Annotated[list[str], append_skill] = Field(default_factory=list)
    turn_count: int = 0


class WorkflowClassification(BaseModel):
    is_answer: bool
    captured_value: str | None = Field(None)
    reply_messages: list[str]


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

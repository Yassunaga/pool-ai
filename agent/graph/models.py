import operator
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

# Ação escolhida pelo LLM a cada turno.
#   - Scripts (emitidos VERBATIM pelo código): greeting/ask_area/ask_name/
#     pitch_urban/pitch_rural/handoff.
#   - faq: desvio para o subagente em contexto isolado.
#   - freeform: o LLM improvisa (ex.: saudação a um cliente que já voltou).
Action = Literal[
    'greeting',
    'ask_area',
    'ask_name',
    'pitch_urban',
    'pitch_rural',
    'handoff',
    'faq',
    'freeform',
]


class Lead(BaseModel):
    """Dados coletados do lead. Hoje: nome e tipo de área."""

    name: str | None = None
    area_type: Literal['urban', 'rural'] | None = None


class Decision(BaseModel):
    """Decisão do turno.

    O LLM escolhe UMA `action`. Quando é um script, o código emite o texto
    canônico verbatim (a copy não passa pelo LLM, garantindo fidelidade às
    regras inegociáveis de preço/prazo). Quando é `freeform`, o LLM improvisa
    e o texto vem em `text`.
    """

    action: Action
    text: str | None = None  # usado apenas quando action == 'freeform'


class ConversationState(BaseModel):
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    lead: Lead = Field(default_factory=Lead)

    # Histórico de ações já executadas. Entregue ao LLM como contexto da
    # decisão, pra ele saber o que já fez (ex.: já saudou, já deu o pitch)
    # sem precisar reler/adivinhar pelo histórico cru.
    skill_path: Annotated[list[str], operator.add] = Field(default_factory=list)

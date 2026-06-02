import sqlite3
import threading
from typing import get_args

from django.conf import settings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .models import ConversationState, Intent
from .nodes import (
    ask_area,
    extract,
    fallback,
    faq,
    greet,
    rural_flow,
    supervisor,
    urban_flow,
)

_graph = None
_graph_lock = threading.Lock()


# Mapeamento intent → nó. Skills ainda não implementadas caem em 'fallback'.
# A paridade com `Intent` é verificada por assertion no `_build_graph` —
# se alguém adicionar intent novo sem mapear, o startup falha alto e cedo.
_INTENT_TO_NODE: dict[str, str] = {
    'greet': 'greet',
    'ask_area': 'ask_area',
    'urban_flow': 'urban_flow',
    'rural_flow': 'rural_flow',
    'faq': 'faq',
    'pricing': 'fallback',
    'schedule': 'fallback',
    'handoff': 'fallback',
    'close': 'fallback',
}


def _route_from_start(state: ConversationState) -> str:
    """Roteia da entrada do grafo: pula extract se já temos area_type."""
    if state.collected_data.area_type is None:
        return 'extract'
    return 'supervisor'


def _route_by_intent(state: ConversationState) -> str:
    """Lê o intent gravado pelo supervisor e devolve o nome do nó destino."""
    return _INTENT_TO_NODE.get(state.intent or '', 'fallback')


def _build_graph():
    # Guard contra drift Intent ↔ _INTENT_TO_NODE.
    assert set(get_args(Intent)) == set(_INTENT_TO_NODE.keys()), (
        'Intent ↔ _INTENT_TO_NODE drift — atualize _INTENT_TO_NODE '
        'para incluir todos os valores de Intent'
    )

    conn = sqlite3.connect(settings.LANGGRAPH_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    workflow = StateGraph(ConversationState)

    workflow.add_node('extract', extract)
    workflow.add_node('supervisor', supervisor)
    workflow.add_node('greet', greet)
    workflow.add_node('ask_area', ask_area)
    workflow.add_node('urban_flow', urban_flow)
    workflow.add_node('rural_flow', rural_flow)
    workflow.add_node('faq', faq)
    workflow.add_node('fallback', fallback)

    # Entrada condicional: extract só roda se ainda não temos area_type.
    workflow.add_conditional_edges(
        START,
        _route_from_start,
        {
            'extract': 'extract',
            'supervisor': 'supervisor',
        },
    )
    workflow.add_edge('extract', 'supervisor')

    # Supervisor escreve `intent` no state; o router lê e despacha.
    workflow.add_conditional_edges(
        'supervisor',
        _route_by_intent,
        {
            'greet': 'greet',
            'ask_area': 'ask_area',
            'urban_flow': 'urban_flow',
            'rural_flow': 'rural_flow',
            'faq': 'faq',
            'fallback': 'fallback',
        },
    )

    workflow.add_edge('greet', END)
    workflow.add_edge('ask_area', END)
    workflow.add_edge('urban_flow', END)
    workflow.add_edge('rural_flow', END)
    workflow.add_edge('faq', END)
    workflow.add_edge('fallback', END)

    return workflow.compile(checkpointer=checkpointer)


def get_graph():
    """Lazy, thread-safe singleton compiled graph."""
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                _graph = _build_graph()
    return _graph

import sqlite3
import threading

from django.conf import settings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .models import ConversationState
from .nodes import fallback, faq, greet, supervisor

_graph = None
_graph_lock = threading.Lock()


# Mapeamento intent → nó. Skills ainda não implementadas caem em 'fallback'.
# Conforme novas skills forem criadas (qualify, pricing, schedule, handoff,
# close), basta adicionar o nó em `_build_graph` e mapear aqui.
_INTENT_TO_NODE: dict[str, str] = {
    'greet': 'greet',
    'faq': 'faq',
    'qualify': 'fallback',
    'pricing': 'fallback',
    'schedule': 'fallback',
    'handoff': 'fallback',
    'close': 'fallback',
}


def _route_by_intent(state: ConversationState) -> str:
    """Lê o intent gravado pelo supervisor e devolve o nome do nó destino."""
    intent = state.get('intent')
    return _INTENT_TO_NODE.get(intent or '', 'fallback')


def _build_graph():
    conn = sqlite3.connect(settings.LANGGRAPH_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    workflow = StateGraph(ConversationState)

    workflow.add_node('supervisor', supervisor)
    workflow.add_node('greet', greet)
    workflow.add_node('faq', faq)
    workflow.add_node('fallback', fallback)

    # Entrada única → supervisor sempre decide.
    workflow.add_edge(START, 'supervisor')

    # Supervisor escreve `intent` no state; o router lê e despacha.
    workflow.add_conditional_edges(
        'supervisor',
        _route_by_intent,
        {
            'greet': 'greet',
            'faq': 'faq',
            'fallback': 'fallback',
        },
    )

    workflow.add_edge('greet', END)
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

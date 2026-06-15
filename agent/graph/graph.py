import sqlite3
import threading

from django.conf import settings
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .models import ConversationState
from .nodes import agent, extract, validate

# Modelos Pydantic próprios que viram parte do checkpoint e precisam ser
# liberados explicitamente para (de)serialização msgpack.
_ALLOWED_MSGPACK_MODULES = (('agent.graph.models', 'Lead'),)

_graph = None
_graph_lock = threading.Lock()


def make_serde() -> JsonPlusSerializer:
    """Serde com os modelos pydantic próprios liberados para msgpack.

    Compartilhado entre o checkpointer de produção (SQLite) e qualquer outro
    (ex.: o ``MemorySaver`` usado pelos evals), pra todos (de)serializarem o
    ``Lead`` da mesma forma."""
    return JsonPlusSerializer(allowed_msgpack_modules=_ALLOWED_MSGPACK_MODULES)


def build_graph(checkpointer):
    """Compila o grafo do agente com o checkpointer dado.

    Fica separado de ``get_graph`` para que os evals possam montar uma instância
    com ``MemorySaver`` (estado em memória, descartável) em vez de tocar o
    ``langgraph_state.sqlite`` de produção."""
    workflow = StateGraph(ConversationState)

    workflow.add_node('extract', extract)
    workflow.add_node('agent', agent)
    workflow.add_node('validate', validate)

    # START → extract (preenche lead) → agent (responde) → validate (guardrail) → END
    workflow.add_edge(START, 'extract')
    workflow.add_edge('extract', 'agent')
    workflow.add_edge('agent', 'validate')
    workflow.add_edge('validate', END)

    return workflow.compile(checkpointer=checkpointer)


def _build_graph():
    conn = sqlite3.connect(settings.LANGGRAPH_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn, serde=make_serde())
    return build_graph(checkpointer)


def get_graph():
    """Lazy, thread-safe singleton compiled graph."""
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                _graph = _build_graph()
    return _graph

import sqlite3
import threading

from django.conf import settings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .models import ConversationState
from .nodes import agent, extract

_graph = None
_graph_lock = threading.Lock()


def _build_graph():
    conn = sqlite3.connect(settings.LANGGRAPH_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    workflow = StateGraph(ConversationState)

    workflow.add_node('extract', extract)
    workflow.add_node('agent', agent)

    # START → extract (preenche lead) → agent (responde) → END
    workflow.add_edge(START, 'extract')
    workflow.add_edge('extract', 'agent')
    workflow.add_edge('agent', END)

    return workflow.compile(checkpointer=checkpointer)


def get_graph():
    """Lazy, thread-safe singleton compiled graph."""
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                _graph = _build_graph()
    return _graph

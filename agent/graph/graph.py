import sqlite3
import threading

from django.conf import settings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .nodes import chatbot, extract_info
from .state import ConversationState

_graph = None
_graph_lock = threading.Lock()


def _build_graph():
    conn = sqlite3.connect(settings.LANGGRAPH_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    workflow = StateGraph(ConversationState)
    workflow.add_node('extract_info', extract_info)
    workflow.add_node('chatbot', chatbot)
    workflow.add_edge(START, 'extract_info')
    workflow.add_edge('extract_info', 'chatbot')
    workflow.add_edge('chatbot', END)

    return workflow.compile(checkpointer=checkpointer)


def get_graph():
    """Lazy, thread-safe singleton compiled graph."""
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                _graph = _build_graph()
    return _graph

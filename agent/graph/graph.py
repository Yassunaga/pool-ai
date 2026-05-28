import sqlite3
import threading

from django.conf import settings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from .nodes import ask_question, close_deal, extract_info, route_after_extract
from .state import ConversationState

_graph = None
_graph_lock = threading.Lock()


def _build_graph():
    conn = sqlite3.connect(settings.LANGGRAPH_DB_PATH, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    workflow = StateGraph(ConversationState)
    workflow.add_node('extract_info', extract_info)
    workflow.add_node('ask_question', ask_question)
    workflow.add_node('close_deal', close_deal)

    workflow.add_edge(START, 'extract_info')
    workflow.add_conditional_edges(
        'extract_info',
        route_after_extract,
        {'ask_question': 'ask_question', 'close_deal': 'close_deal'},
    )
    workflow.add_edge('ask_question', END)
    workflow.add_edge('close_deal', END)

    return workflow.compile(checkpointer=checkpointer)


def get_graph():
    """Lazy, thread-safe singleton compiled graph."""
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                _graph = _build_graph()
    return _graph

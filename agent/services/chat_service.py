from langchain_core.messages import AIMessage, HumanMessage

from ..graph import get_graph


def send_message(session_id: str, message: str) -> dict:
    """Run one turn of the sales conversation for the given session."""
    graph = get_graph()
    config = {'configurable': {'thread_id': session_id}}

    result = graph.invoke(
        {'messages': [HumanMessage(content=message)]},
        config=config,
    )

    # Collect every AIMessage at the tail of the history — those are the
    # replies emitted during this turn (possibly multiple).
    replies: list[str] = []
    for m in reversed(result['messages']):
        if isinstance(m, AIMessage):
            replies.append(m.content)
        else:
            break
    replies.reverse()

    return {
        'session_id': session_id,
        'replies': replies,
        'collected_data': result.get('collected_data') or {},
        'workflow_step': result.get('workflow_step'),
    }

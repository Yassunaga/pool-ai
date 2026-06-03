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
    }

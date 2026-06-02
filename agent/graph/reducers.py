"""Reducers para campos do `ConversationState` que precisam de merge custom.

Módulo isolado de propósito: importado por `models.py` e por `utils.py`,
não pode depender de nenhum dos dois (evita import circular).
"""


def append_skill(left: list[str] | None, right: list[str] | None) -> list[str]:
    """Reducer para `skill_path`: concatena tolerando None de qualquer lado."""
    return (left or []) + (right or [])

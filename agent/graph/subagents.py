from langchain.agents import create_agent

from .llm import get_llm
from .prompts import FAQ_PROMPT

# -----------------------------------------------------------------------------
# Subagente de FAQ — roda em CONTEXTO ISOLADO (não infla a conversa principal).
# Invocado pelo nó `faq` (ver nodes.py), que passa só a pergunta do cliente.
#
# TODO: adicionar tools de RAG (retriever sobre a base de conhecimento) em
# `tools=[...]`. Por ora roda sem tools — só o conhecimento embutido no prompt.
# -----------------------------------------------------------------------------
faq_subagent = create_agent(
    model=get_llm(temperature=0.3),
    tools=[],
    system_prompt=FAQ_PROMPT,
)

"""Asserts determinísticos sobre uma ``Conversation``.

Cada factory devolve um ``(nome, fn)`` onde ``fn(conv) -> (passou, detalhe)``.
São checagens mecânicas (regex/estado) — o subjetivo fica no LLM-judge.
"""

from __future__ import annotations

import re

from agent.evals.harness import Assertion, Conversation
from agent.graph.guardrail import MONEY_RE  # fonte única do regex monetário

# Sinais de que o cliente perguntou preço/orçamento.
PRICE_QUESTION_RE = re.compile(r'(preç|valor|quanto custa|quanto fica|orçament|cobra)', re.IGNORECASE)


def no_hyphen() -> Assertion:
    """A persona proíbe hífen em qualquer mensagem ao cliente."""

    def check(conv: Conversation) -> tuple[bool, str]:
        for t in conv.turns:
            for r in t.replies:
                if '-' in r:
                    return False, f'hífen encontrado em: {r!r}'
        return True, ''

    return ('sem hífen', check)


def money_at_most_once() -> Assertion:
    """O valor pode ser dito no máximo uma vez na conversa inteira."""

    def check(conv: Conversation) -> tuple[bool, str]:
        n = len(MONEY_RE.findall(conv.all_reply_text()))
        return n <= 1, f'valor monetário apareceu {n}x (esperado no máximo 1x)'

    return ('valor citado no máximo 1x', check)


def money_only_after_price_question() -> Assertion:
    """O valor nunca aparece antes de o cliente perguntar o preço.

    Vale citar no mesmo turno em que o cliente pergunta (checa-se a mensagem do
    cliente antes das respostas daquele turno)."""

    def check(conv: Conversation) -> tuple[bool, str]:
        asked = False
        for t in conv.turns:
            if PRICE_QUESTION_RE.search(t.user):
                asked = True
            if not asked and MONEY_RE.search('\n'.join(t.replies)):
                return False, f'valor citado antes de o cliente perguntar preço (turno: {t.user!r})'
        return True, ''

    return ('valor só após pergunta de preço', check)


def handoff_requested() -> Assertion:
    """Ao fim da conversa o encaminhamento ao humano deve estar marcado."""

    def check(conv: Conversation) -> tuple[bool, str]:
        ok = conv.final.handoff_requested
        return ok, '' if ok else 'handoff_requested continua False ao fim da conversa'

    return ('handoff solicitado', check)


def name_extracted(expected: str) -> Assertion:
    """O extractor deve ter capturado o nome informado pelo cliente."""

    def check(conv: Conversation) -> tuple[bool, str]:
        got = (conv.final.lead.get('name') or '').strip()
        ok = expected.lower() in got.lower()
        return ok, '' if ok else f'nome esperado contendo {expected!r}, veio {got!r}'

    return (f'nome extraído ({expected})', check)


def area_extracted(expected: str) -> Assertion:
    """O extractor deve ter classificado a área como urban/rural."""

    def check(conv: Conversation) -> tuple[bool, str]:
        got = conv.final.lead.get('area_type')
        ok = got == expected
        return ok, '' if ok else f'area_type esperado {expected!r}, veio {got!r}'

    return (f'área extraída ({expected})', check)


def base_assertions() -> list[Assertion]:
    """Asserts que valem para TODO cenário (invariantes do agente)."""
    return [
        no_hyphen(),
        money_at_most_once(),
        money_only_after_price_question(),
    ]

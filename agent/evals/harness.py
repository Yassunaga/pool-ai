"""Núcleo do harness de evals do agente.

Roda cada cenário (um roteiro fixo de mensagens do "cliente") contra o grafo
real, mas com um ``MemorySaver`` descartável em vez do checkpointer SQLite de
produção — assim a suíte não toca o estado de produção nem o banco Django.

Cada cenário vira uma ``Conversation`` (lista de ``Turn``), sobre a qual rodam:
- asserts determinísticos (regex/estado) — ver ``assertions.py``;
- opcionalmente um LLM-judge para o subjetivo — ver ``judge.py``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agent.graph.graph import build_graph, make_serde
from agent.services.chat_service import collect_replies

# Um assert é (nome, fn); fn recebe a Conversation e devolve (passou, detalhe).
Assertion = tuple[str, Callable[['Conversation'], tuple[bool, str]]]


@dataclass
class Turn:
    """Um turno: a mensagem do cliente, as respostas do bot e o estado depois."""

    user: str
    replies: list[str]
    lead: dict
    handoff_requested: bool


@dataclass
class Conversation:
    scenario_id: str
    turns: list[Turn]

    def all_reply_text(self) -> str:
        return '\n'.join(r for t in self.turns for r in t.replies)

    @property
    def final(self) -> Turn:
        return self.turns[-1]


@dataclass
class Scenario:
    """Um caso de teste: roteiro do cliente + o que validar."""

    id: str
    description: str
    messages: list[str]
    assertions: list[Assertion]
    judge: bool = True


@dataclass
class ScenarioResult:
    scenario: Scenario
    conversation: Conversation
    assert_results: list[tuple[str, bool, str]]
    judge_verdict: object | None = field(default=None)
    error: str | None = None

    @property
    def asserts_passed(self) -> bool:
        return all(ok for _, ok, _ in self.assert_results)

    @property
    def judge_passed(self) -> bool:
        # Sem judge => não reprova por isso. Com judge: não pode inventar fato e
        # a nota tem que ser >= 3 (escala 1-5).
        v = self.judge_verdict
        if v is None:
            return True
        return (not v.inventou_fato) and v.nota >= 3

    @property
    def passed(self) -> bool:
        return self.error is None and self.asserts_passed and self.judge_passed


def build_eval_graph():
    """Grafo com estado em memória (nada é persistido entre execuções)."""
    return build_graph(MemorySaver(serde=make_serde()))


def run_scenario(graph, scenario: Scenario, use_judge: bool) -> ScenarioResult:
    """Roda um cenário ponta a ponta e avalia os asserts (+ judge opcional)."""
    thread_id = f'eval-{scenario.id}-{uuid.uuid4().hex[:8]}'
    config = {'configurable': {'thread_id': thread_id}}

    turns: list[Turn] = []
    try:
        for user_msg in scenario.messages:
            result = graph.invoke(
                {'messages': [HumanMessage(content=user_msg)]},
                config=config,
            )
            lead = result['lead']
            turns.append(
                Turn(
                    user=user_msg,
                    replies=collect_replies(result),
                    lead={'name': lead.name, 'area_type': lead.area_type},
                    handoff_requested=bool(result.get('handoff_requested')),
                )
            )
    except Exception as exc:  # noqa: BLE001 — um cenário que explode não derruba a suíte
        conv = Conversation(scenario.id, turns)
        return ScenarioResult(scenario, conv, [], error=f'{type(exc).__name__}: {exc}')

    conv = Conversation(scenario.id, turns)
    assert_results = [(name, *fn(conv)) for name, fn in scenario.assertions]

    verdict = None
    if use_judge and scenario.judge:
        from agent.evals.judge import judge_conversation

        try:
            verdict = judge_conversation(conv)
        except Exception as exc:  # noqa: BLE001
            assert_results.append(('judge (erro)', False, f'{type(exc).__name__}: {exc}'))

    return ScenarioResult(scenario, conv, assert_results, judge_verdict=verdict)


def run_suite(scenarios: list[Scenario], use_judge: bool = True) -> list[ScenarioResult]:
    graph = build_eval_graph()
    return [run_scenario(graph, s, use_judge) for s in scenarios]

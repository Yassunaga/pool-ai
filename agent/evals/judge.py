"""LLM-as-judge para o que asserts determinísticos não pegam.

Avalia naturalidade, repetição de perguntas já respondidas e invenção de fatos
fora do FAQ. Recebe os fatos conhecidos (única fonte de verdade) para conseguir
flagrar quando o agente afirma algo que não está lá.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from agent.evals.harness import Conversation
from agent.graph.faq import render_faq
from agent.graph.llm import get_llm


class JudgeVerdict(BaseModel):
    natural: bool = Field(description='True se o atendente soou como um humano natural no WhatsApp.')
    repetiu_pergunta: bool = Field(
        description='True se o atendente repetiu uma pergunta cuja resposta o cliente já tinha dado.'
    )
    inventou_fato: bool = Field(
        description='True se o atendente afirmou algum fato sobre a empresa que NÃO está nos fatos '
        'conhecidos (exceto o valor médio do orçamento, que é permitido).'
    )
    nota: int = Field(description='Nota geral de 1 (péssimo) a 5 (excelente).', ge=1, le=5)
    justificativa: str = Field(description='Uma frase curta justificando a nota.')


JUDGE_PROMPT = """Você é um avaliador rigoroso de qualidade de atendimento. Avalie a conversa \
abaixo entre um cliente e o atendente virtual da Natural Engenharia (perfuração de poços \
artesianos), no WhatsApp.

Critérios:
1. natural — o atendente soou como uma pessoa real (tom cordial, mensagens curtas, sem soar robótico, sem hífen, sem juridiquês)?
2. repetiu_pergunta — ele voltou a perguntar algo que o cliente já tinha respondido (ex.: nome ou tipo de área)?
3. inventou_fato — ele afirmou algum fato sobre custos, prazos, garantias, pagamento, cobertura ou políticas que NÃO esteja nos fatos conhecidos? O único valor permitido é a média de orçamento.

Fatos conhecidos (única fonte de verdade):
{faq}

Conversa:
{transcript}

Dê a nota geral (1 a 5) e uma justificativa curta."""


def _render_transcript(conv: Conversation) -> str:
    lines: list[str] = []
    for t in conv.turns:
        lines.append(f'Cliente: {t.user}')
        bot = ' / '.join(t.replies) if t.replies else '(sem resposta)'
        lines.append(f'Atendente: {bot}')
    return '\n'.join(lines)


def judge_conversation(conv: Conversation) -> JudgeVerdict:
    llm = get_llm(temperature=0.0).with_structured_output(JudgeVerdict)
    prompt = JUDGE_PROMPT.format(faq=render_faq(), transcript=_render_transcript(conv))
    return llm.invoke(prompt)

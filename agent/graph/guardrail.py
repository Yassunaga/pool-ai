"""Guardrail determinístico sobre os chunks de resposta, antes do envio.

Regra de prompt nunca garante nada; este módulo é a checagem mecânica que de fato
impede valor/conteúdo proibido de chegar ao cliente. É chamado pelo nó `validate`
(entre `agent` e `END`).

Fonte única do regex monetário: os evals (`agent/evals/assertions.py`) importam
``MONEY_RE`` daqui para não duplicar a regra.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# "R$ 8.000,00", "R$8000" etc. — o único valor permitido vem da tool build_budget.
MONEY_RE = re.compile(r'R\$\s*\d')
# Expressão monetária completa, para remover o valor inteiro ao sanitizar.
MONEY_EXPR_RE = re.compile(r'R\$\s*\d[\d.,]*')

# Chunk de WhatsApp deve ser curto; acima disso o guardrail trata.
MAX_CHUNK_LEN = 500

# Mensagem segura quando a sanitização esvazia a resposta (ex.: todo o conteúdo
# era um valor não autorizado, removido). Sem hífen, sem número.
SAFE_FALLBACK = 'Sobre valores, quem confirma certinho é o nosso especialista. Posso te encaminhar?'


@dataclass
class Violations:
    money: bool = False
    hyphen: bool = False
    too_long: bool = False

    @property
    def any(self) -> bool:
        return self.money or self.hyphen or self.too_long

    def describe(self) -> list[str]:
        out: list[str] = []
        if self.money:
            out.append('citou um valor monetário (R$) que NÃO está autorizado neste turno')
        if self.hyphen:
            out.append('usou hífen (-), proibido pela persona')
        if self.too_long:
            out.append(f'mandou uma mensagem com mais de {MAX_CHUNK_LEN} caracteres')
        return out


def detect(chunks: list[str], money_allowed: bool) -> Violations:
    """Detecta violações nos chunks deste turno.

    ``money_allowed`` indica que o turno entregou legitimamente o valor médio
    (``build_budget`` rodou e o valor ainda não tinha sido dado), caso em que UMA
    menção monetária é permitida; qualquer outra é violação."""
    v = Violations()

    money_count = sum(len(MONEY_RE.findall(c)) for c in chunks)
    if money_count > (1 if money_allowed else 0):
        v.money = True
    if any('-' in c for c in chunks):
        v.hyphen = True
    if any(len(c) > MAX_CHUNK_LEN for c in chunks):
        v.too_long = True

    return v


def _strip_hyphen(text: str) -> str:
    text = text.replace('-', ' ')
    return re.sub(r'\s{2,}', ' ', text).strip()


def _enforce_money(text: str, budget: list[int]) -> str:
    """Mantém até ``budget[0]`` expressões monetárias e remove o resto.

    ``budget`` é uma lista de 1 int (contador mutável) compartilhada entre os
    chunks, para o limite valer na resposta inteira, não por chunk."""

    def repl(m: re.Match) -> str:
        if budget[0] > 0:
            budget[0] -= 1
            return m.group(0)
        return ''

    text = MONEY_EXPR_RE.sub(repl, text)
    # Limpa o que a remoção deixou para trás: espaços duplos e pontuação órfã.
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\s+([,.!?])', r'\1', text)
    return text.strip(' ,;')


def _truncate(text: str) -> str:
    if len(text) <= MAX_CHUNK_LEN:
        return text
    cut = text[:MAX_CHUNK_LEN].rsplit(' ', 1)[0].rstrip()
    return cut or text[:MAX_CHUNK_LEN].rstrip()


def sanitize(chunks: list[str], money_allowed: bool) -> list[str]:
    """Correções determinísticas que GARANTEM o invariante (a regeneração via LLM
    é só best-effort; isto é o que de fato bloqueia o envio).

    Remove hífens, mantém no máximo a quantidade permitida de valores monetários e
    corta chunks longos demais. Se sobrar vazio, devolve uma mensagem segura."""
    budget = [1 if money_allowed else 0]
    out: list[str] = []
    for c in chunks:
        c = _strip_hyphen(c)
        c = _enforce_money(c, budget)
        c = _truncate(c).strip()
        if c:
            out.append(c)
    return out or [SAFE_FALLBACK]

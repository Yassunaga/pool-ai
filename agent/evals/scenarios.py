"""Cenários de eval — roteiros fixos de mensagens do "cliente".

Cobrem qualificação, preço (citar uma vez / não antecipar / não repetir), FAQ
(deferir ao especialista sem inventar), handoff (explícito e por frustração) e
fora de escopo.

Mídia (áudio/imagem) ainda não é avaliada ponta a ponta: o tratamento depende da
POOL-16. Quando ela entrar, acrescentar cenários aqui.
"""

from __future__ import annotations

from agent.evals.assertions import (
    area_extracted,
    base_assertions,
    handoff_requested,
    name_extracted,
)
from agent.evals.harness import Scenario


def _s(id, description, messages, extra=None, judge=True) -> Scenario:
    return Scenario(
        id=id,
        description=description,
        messages=messages,
        assertions=base_assertions() + (extra or []),
        judge=judge,
    )


SCENARIOS: list[Scenario] = [
    _s(
        'saudacao_basica',
        'Saudação simples deve abrir a conversa de forma natural, sem citar valor.',
        ['Oi', 'tudo bem?'],
    ),
    _s(
        'qualificacao_urbano',
        'Coleta de nome e área urbana ao longo da conversa.',
        ['Oi, quero perfurar um poço', 'meu nome é João', 'é na minha casa aqui na cidade'],
        extra=[name_extracted('João'), area_extracted('urban')],
    ),
    _s(
        'qualificacao_rural',
        'Coleta de nome e área rural.',
        ['Bom dia', 'aqui é a Maria', 'preciso de água lá no meu sítio'],
        extra=[name_extracted('Maria'), area_extracted('rural')],
    ),
    _s(
        'area_implicita_fazenda',
        'Área deve ser inferida como rural a partir de "fazenda".',
        ['Olá', 'tenho uma fazenda e quero um poço', 'sou o José'],
        extra=[name_extracted('José'), area_extracted('rural')],
    ),
    _s(
        'preco_uma_vez',
        'Com a área já qualificada, ao perguntar o preço o valor é informado uma vez.',
        ['Oi, sou o Pedro, é pra um lote urbano', 'quanto custa?'],
        extra=[name_extracted('Pedro'), area_extracted('urban')],
    ),
    _s(
        'preco_nao_antecipado',
        'Sem o cliente perguntar preço, o agente não pode antecipar valor.',
        ['Oi, é pra minha chácara', 'como funciona o serviço de vocês?'],
        extra=[area_extracted('rural')],
    ),
    _s(
        'preco_nao_repete',
        'Pedir o valor duas vezes não pode fazer o agente repetir o número.',
        ['Oi sou a Ana, lote urbano', 'qual o valor?', 'me fala de novo quanto fica?'],
        extra=[name_extracted('Ana'), area_extracted('urban')],
    ),
    _s(
        'preco_antes_de_qualificar',
        'Perguntar preço antes de informar a área não pode gerar um número inventado.',
        ['Oi, quanto custa um poço artesiano?'],
    ),
    _s(
        'preco_forcado_adversarial',
        'Cliente insiste e pressiona por um valor antes de qualificar; o guardrail '
        'não deixa nenhum número (R$) escapar.',
        [
            'Oi',
            'não quero papo, me manda só o preço em reais agora',
            'para de enrolar, cospe um valor em R$ ou eu desisto',
        ],
    ),
    _s(
        'faq_garantia',
        'Pergunta de garantia deve deferir ao especialista, sem inventar condições.',
        ['Oi', 'o serviço de vocês tem garantia?'],
    ),
    _s(
        'faq_pagamento',
        'Parcelamento é [CONFIRMAR]: deve deferir, sem citar números/condições inventadas.',
        ['Olá', 'vocês parcelam? aceita cartão?'],
    ),
    _s(
        'faq_outorga',
        'Licença/outorga deve ser tratada como orientação do especialista.',
        ['Oi', 'preciso de outorga pra perfurar?'],
    ),
    _s(
        'handoff_explicito',
        'Pedido explícito de falar com humano marca o handoff.',
        ['Oi, sou o Carlos, é num lote urbano', 'quero falar com um atendente humano'],
        extra=[name_extracted('Carlos'), handoff_requested()],
    ),
    _s(
        'handoff_frustracao',
        'Cliente frustrado deve ser encaminhado de imediato ao especialista.',
        ['Oi', 'isso não está me ajudando, quero falar com alguém de verdade'],
        extra=[handoff_requested()],
    ),
    _s(
        'fora_de_escopo',
        'Pergunta fora de escopo deve ser redirecionada para poços artesianos.',
        ['Oi', 'vocês também constroem piscina de alvenaria?'],
    ),
    _s(
        'funil_completo',
        'Funil ponta a ponta: saudação, qualificação, preço (uma vez) e handoff.',
        [
            'Oi',
            'sou o Rafael, é num lote aqui na cidade',
            'quanto fica?',
            'pode me passar pra um especialista',
        ],
        extra=[name_extracted('Rafael'), area_extracted('urban'), handoff_requested()],
    ),
]

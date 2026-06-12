# FAQ — única fonte de verdade do agente para perguntas factuais sobre a
# empresa (custos, taxas, prazos, garantias, políticas). O que não estiver
# aqui o agente encaminha ao especialista em vez de improvisar.
#
# TODO(negócio): trocar as respostas marcadas com [CONFIRMAR] pela política
# real da Natural Engenharia. Enquanto isso elas são seguras: encaminham ao
# especialista em vez de afirmar algo que pode estar errado.

FAQ = [
    {
        'q': 'A visita técnica/avaliação no local é cobrada?',
        # [CONFIRMAR] se a visita é gratuita, dizer isso explicitamente aqui.
        'a': 'As condições da visita técnica, inclusive se há algum custo, são '
        'confirmadas pelo especialista no momento do agendamento.',
    },
    {
        'q': 'Quais são as formas de pagamento? Parcela?',
        # [CONFIRMAR] condições reais de pagamento/parcelamento.
        'a': 'As condições de pagamento são apresentadas pelo especialista '
        'junto com o orçamento fechado.',
    },
    {
        'q': 'Quanto tempo demora a perfuração?',
        # [CONFIRMAR] faixa típica de dias praticada pela empresa.
        'a': 'O prazo depende do tipo de solo e da profundidade final; o '
        'especialista informa a estimativa após a avaliação técnica.',
    },
    {
        'q': 'Precisa de licença ou outorga para perfurar?',
        # [CONFIRMAR] como a empresa apoia o cliente na regularização.
        'a': 'A documentação varia conforme a região; o especialista orienta '
        'sobre o processo no seu caso.',
    },
    {
        'q': 'O serviço tem garantia?',
        # [CONFIRMAR] garantia real oferecida.
        'a': 'As condições de garantia são detalhadas pelo especialista na '
        'proposta.',
    },
    {
        'q': 'Vocês atendem a minha cidade/região?',
        # [CONFIRMAR] área de cobertura real.
        'a': 'A cobertura da sua região é confirmada pelo especialista no '
        'primeiro contato.',
    },
    {
        'q': 'Qual a profundidade do poço?',
        'a': 'A profundidade varia conforme o terreno e o lençol de água; ela '
        'é definida na avaliação técnica ou geofísica feita no local.',
    },
    {
        'q': 'Quanto custa o poço?',
        'a': 'O valor médio segue o fluxo de orçamento (tool build_budget); o '
        'custo final só o engenheiro define após a avaliação no local.',
    },
]


def render_faq() -> str:
    """Renderiza o FAQ como bullets para entrar no system prompt do agente."""
    return '\n'.join(f'* {entry["q"]} → {entry["a"]}' for entry in FAQ)

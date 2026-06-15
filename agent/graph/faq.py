# FAQ — única fonte de verdade do agente para perguntas factuais sobre a
# empresa (custos, taxas, prazos, garantias, políticas). O que não estiver
# aqui o agente encaminha ao especialista em vez de improvisar.

FAQ = [
    {
        'q': 'A visita técnica/avaliação no local é cobrada?',
        'a': 'Na maioria dos casos não é necessária visita técnica: o '
        'orçamento é feito à distância, já que conhecemos bem toda a região. '
        'Quando há necessidade (situações mais específicas), a visita pode ser '
        'feita, e não há cobrança pela visita em si — o que pode ser cobrado é '
        'o deslocamento, conforme a distância.',
    },
    {
        'q': 'Quais são as formas de pagamento? Parcela?',
        'a': 'O pagamento é feito em 50% para iniciar o serviço e 50% na '
        'entrega. Outras condições podem ser negociadas caso a caso com o '
        'especialista.',
    },
    {
        'q': 'Quanto tempo demora a perfuração?',
        'a': 'A perfuração leva em média de 3 a 4 dias, dependendo da '
        'complexidade do solo a ser perfurado.',
    },
    {
        'q': 'Precisa de licença ou outorga para perfurar?',
        'a': 'A perfuração é feita com ART (Anotação de Responsabilidade '
        'Técnica) emitida pela empresa junto ao CREA, o que garante a '
        'regularidade técnica da obra. Caso o cliente precise de outorga ou '
        'licenciamento ambiental, o especialista orienta sobre o processo.',
    },
    {
        'q': 'O serviço tem garantia?',
        'a': 'Sim. O serviço tem garantia total de 1 ano.',
    },
    {
        'q': 'Vocês atendem a minha cidade/região?',
        'a': 'Atendemos todo o estado de Roraima, em todos os municípios sem '
        'exceção. O valor do serviço é basicamente o mesmo para todos; o que '
        'varia é o acréscimo de deslocamento, conforme a distância.',
    },
    {
        'q': 'Qual a profundidade do poço?',
        'a': 'A profundidade varia conforme o terreno e o lençol de água e é '
        'definida na avaliação técnica ou geofísica feita no local. Como '
        'referência, poços semi-artesianos costumam ficar entre 20 e 30 metros '
        'e os artesianos acima de 30 metros, frequentemente ultrapassando 60.',
    },
    {
        'q': 'Qual a diferença entre poço semi-artesiano e artesiano?',
        'a': 'O poço semi-artesiano em geral tem profundidade entre 20 e 30 '
        'metros. O poço artesiano fica acima de 30 metros e, na maior parte '
        'dos casos, ultrapassa 60 metros, podendo chegar a 80 ou até cerca de '
        '100 metros, conforme a profundidade em que se encontra água '
        'suficiente.',
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

from langchain_core.tools import tool

from .models import Lead


@tool
def greeting_instructions() -> str:
    """Retorna as instruções de como saudar o cliente na PRIMEIRA mensagem da
    conversa. Chame esta tool no início de um atendimento novo, antes de
    responder ao cliente, para saber o tom e o conteúdo da saudação de abertura."""
    TEXT = """
    Use esse texto na primeira saudação: Oi! Bem Vindo à Natural Engenharia! Empresa referência no segmento de perfuração de poços artesianos!
    Se o usuário já foi saudado, só responda a saudação dele normalmente.
    """

    return TEXT


# Valores base de orçamento por tipo de área (R$). Ilustrativos/configuráveis —
# ajuste conforme a tabela real da Natural Engenharia.
BUDGET_BY_AREA = {
    'urban': 8000.0,
    'rural': 10000.0,
}


def make_build_budget(lead: Lead):
    """Cria a tool `build_budget` amarrada ao `lead` do estado atual (closure),
    já que o loop ReAct interno do `create_agent` só recebe as mensagens."""

    @tool
    def build_budget() -> str:
        """Monta o orçamento do poço artesiano calculando o valor com base no
        tipo de área do lead (urbano/rural). Use esta tool quando precisar do
        valor estimado do orçamento. Se o tipo de área ainda não foi informado,
        a tool avisa que é preciso qualificar o lead antes."""
        value = BUDGET_BY_AREA.get(lead.area_type)
        if value is None:
            return (
                'Tipo de área ainda não informado — qualifique o lead '
                '(urbano ou rural) antes de montar o orçamento.'
            )

        AREA_LABELS = {'urban': 'urbano', 'rural': 'rural'}
        name = lead.name or 'cliente'
        area = AREA_LABELS[lead.area_type]
        value_fmt = f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

        return (
            f'Orçamento para {name}:\n'
            f'- Tipo de área: {area}\n'
            f'- Valor estimado: {value_fmt}'
        )

    return build_budget


def make_retrieve_lead_information(lead: Lead):
    """Cria a tool `retrieve_lead_information` já amarrada ao `lead` do estado
    atual (via closure), já que o loop ReAct interno do `create_agent` só recebe
    as mensagens — o `lead` vive no `ConversationState` externo."""

    @tool
    def retrieve_lead_information() -> str:
        """Retorna os dados já coletados do lead (usuário): nome e tipo de área
        (urbano/rural). Use esta tool quando precisar saber informações do lead
        para não repetir perguntas e adequar o atendimento ao caso."""
        AREA_LABELS = {'urban': 'urbano', 'rural': 'rural'}

        name = lead.name or 'não informado'
        area = AREA_LABELS.get(lead.area_type, 'não identificado')

        return f'Dados do lead:\n- Nome: {name}\n- Tipo de área: {area}'

    return retrieve_lead_information

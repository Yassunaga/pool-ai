from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    scripted_messages: tuple[str, ...]
    question: str
    captured_field: str | None
    next_step: str | None


INITIAL_STEP_ID = 'welcome'
FREE_FORM_STEP_ID = 'free_form'

WORKFLOW: dict[str, WorkflowStep] = {
    'welcome': WorkflowStep(
        id='welcome',
        scripted_messages=(
            'Oi! Bem Vindo à Natural Engenharia! Empresa referência no segmento de perfuração de poços artesianos!',
            'Vi que está interessado em ter seu próprio poço artesiano e não ter mais problemas para ter água! Esse é o caminho certo!',
            'Para começar a te ajudar a não ter mais falta de água em nenhum momento, preciso saber: você vai querer um poço artesiano na cidade ou na área rural?',
        ),
        question='Você vai querer um poço artesiano na cidade ou na área rural?',
        captured_field='location_type',
        next_step=None,
    ),
}

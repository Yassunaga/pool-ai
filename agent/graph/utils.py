from agent.graph.models import (
    CollectedData,
    FIELD_LABELS,
    REQUIRED_FIELDS,
)


def _format_summaries(collected: CollectedData) -> tuple[str, str]:
    collected_lines = []
    missing_lines = []
    for field in REQUIRED_FIELDS:
        label = FIELD_LABELS[field]
        value = collected.get(field)
        if value:
            collected_lines.append(f'- {label}: {value}')
        else:
            missing_lines.append(f'- {label}')

    collected_summary = '\n'.join(collected_lines) or '- (nenhuma ainda)'
    missing_summary = '\n'.join(missing_lines) or '- (todas coletadas)'
    return collected_summary, missing_summary


_FAQ_CONTEXT_LABELS: dict[str, str] = {
    'location': 'localização',
    'location_type': 'tipo de área (urbana/rural)',
    'depth': 'profundidade estimada',
    'purpose': 'finalidade',
    'flow_rate': 'vazão desejada',
    'terrain': 'tipo de terreno',
}


def _append_skill(left: list[str] | None, right: list[str] | None) -> list[str]:
    """Reducer para skill_path: concatena tolerando None de qualquer lado."""
    return (left or []) + (right or [])


def _format_collected_context(collected: CollectedData) -> str:
    """Versão narrativa do collected_data, para contextualizar o FAQ."""
    if not collected:
        return '(o cliente ainda não forneceu informações específicas sobre o caso dele)'

    items = []
    for field, label in _FAQ_CONTEXT_LABELS.items():
        value = collected.get(field)
        if value:
            items.append(f'{label}: {value}')

    if not items:
        return '(o cliente ainda não forneceu informações específicas)'
    return '; '.join(items)

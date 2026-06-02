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
        value = getattr(collected, field, None)
        if value:
            collected_lines.append(f'- {label}: {value}')
        else:
            missing_lines.append(f'- {label}')

    collected_summary = '\n'.join(collected_lines) or '- (nenhuma ainda)'
    missing_summary = '\n'.join(missing_lines) or '- (todas coletadas)'
    return collected_summary, missing_summary


_FAQ_CONTEXT_LABELS: dict[str, str] = {
    'area_type': 'tipo de área (urbano ou rural)',
}


def _format_collected_context(collected: CollectedData) -> str:
    """Versão narrativa do collected_data, para contextualizar o FAQ."""
    items = []
    for field, label in _FAQ_CONTEXT_LABELS.items():
        value = getattr(collected, field, None)
        if value:
            items.append(f'{label}: {value}')

    if not items:
        return '(o cliente ainda não forneceu informações específicas)'
    return '; '.join(items)

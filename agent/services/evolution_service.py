import httpx
from django.conf import settings


def send_text(number: str, text: str) -> dict:
    """Send a WhatsApp text message back through the Evolution API.

    Mostra o presence 'composing' (digitando…) por um tempo proporcional ao
    tamanho do texto (settings.EVOLUTION_TYPING_MS_PER_CHAR) antes de entregar.
    """
    delay_ms = len(text) * settings.EVOLUTION_TYPING_MS_PER_CHAR
    url = f'{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE}'
    response = httpx.post(
        url,
        headers={'apikey': settings.EVOLUTION_API_KEY},
        json={
            'number': number,
            'text': text,
            'delay': delay_ms,
            'presence': 'composing',
        },
        timeout=30 + delay_ms / 1000,
    )
    response.raise_for_status()
    return response.json()

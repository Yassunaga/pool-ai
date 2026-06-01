import httpx
from django.conf import settings


def send_text(number: str, text: str) -> dict:
    """Send a WhatsApp text message back through the Evolution API."""
    url = f'{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE}'
    response = httpx.post(
        url,
        headers={'apikey': settings.EVOLUTION_API_KEY},
        json={'number': number, 'text': text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

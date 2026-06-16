"""Baixa e interpreta mídia (áudio/imagem) do WhatsApp via Evolution + OpenRouter.

POOL-16: áudio é ~metade do tráfego do WhatsApp no Brasil; sem tratá-lo o cliente
que manda áudio fica em silêncio (maior delator de bot). Aqui baixamos a mídia da
Evolution (``/chat/getBase64FromMediaMessage``), transcrevemos áudio e descrevemos
imagem via modelo multimodal no OpenRouter, e devolvemos **texto** para o fluxo
normal de debounce/grafo seguir como se o cliente tivesse digitado.

Os modelos vêm de ``settings.OPENROUTER_TRANSCRIBE_MODEL`` (áudio) e
``OPENROUTER_VISION_MODEL`` (imagem). Tudo reusa ``OPENROUTER_API_KEY`` — nenhuma
chave nova é necessária.
"""

import logging

import httpx
from django.conf import settings
from langchain_core.messages import HumanMessage

from ..graph.llm import get_llm

logger = logging.getLogger(__name__)

# Resposta literal pedida quando o áudio não contém fala, para o chamador tratar
# como "vazio" em vez de mandar uma transcrição inútil pro agente.
_NO_SPEECH = '[sem fala]'

_TRANSCRIBE_PROMPT = (
    'Transcreva o áudio a seguir literalmente, em português do Brasil. '
    'Responda apenas com a transcrição, sem comentários e sem aspas. '
    f'Se não houver fala compreensível, responda exatamente: {_NO_SPEECH}'
)

_VISION_PROMPT = (
    'Você está ajudando o atendimento de uma empresa de perfuração de poços '
    'artesianos. O cliente enviou esta imagem pelo WhatsApp. Descreva de forma '
    'objetiva, em português (1-2 frases), o que aparece e o que pode ser '
    'relevante para o atendimento (ex.: terreno, documento, foto de um local, '
    'equipamento, conta de água). Responda só com a descrição.'
)

# Áudio do WhatsApp chega como OGG/Opus; o mimetype pode vir com parâmetros
# (ex.: "audio/ogg; codecs=opus") que quebram o formato esperado pela API.
_DEFAULT_AUDIO_MIME = 'audio/ogg'
_DEFAULT_IMAGE_MIME = 'image/jpeg'


def _clean_mimetype(mimetype: str | None, default: str) -> str:
    """Tira parâmetros do mimetype ('audio/ogg; codecs=opus' -> 'audio/ogg')."""
    if not mimetype:
        return default
    return mimetype.split(';', 1)[0].strip() or default


def download_media_base64(key: dict) -> tuple[str, str | None]:
    """Baixa a mídia de uma mensagem via Evolution e devolve (base64, mimetype).

    A Evolution localiza a mídia pelo ``key.id`` no próprio store, então basta
    mandar a ``key`` recebida no webhook.
    """
    url = (
        f'{settings.EVOLUTION_API_URL}'
        f'/chat/getBase64FromMediaMessage/{settings.EVOLUTION_INSTANCE}'
    )
    response = httpx.post(
        url,
        headers={'apikey': settings.EVOLUTION_API_KEY},
        json={'message': {'key': key}, 'convertToMp4': False},
        timeout=60,
    )
    response.raise_for_status()
    body = response.json()
    return body['base64'], body.get('mimetype')


def transcribe_audio_message(audio_message: dict, key: dict) -> str:
    """Baixa o áudio da mensagem e devolve a transcrição (ou ``''`` se sem fala)."""
    base64_data, mimetype = download_media_base64(key)
    mimetype = _clean_mimetype(mimetype or audio_message.get('mimetype'), _DEFAULT_AUDIO_MIME)

    llm = get_llm(temperature=0.0, model=settings.OPENROUTER_TRANSCRIBE_MODEL)
    result = llm.invoke([
        HumanMessage(content=[
            {'type': 'text', 'text': _TRANSCRIBE_PROMPT},
            {'type': 'audio', 'base64': base64_data, 'mime_type': mimetype},
        ])
    ])

    transcript = (result.content or '').strip()
    if transcript == _NO_SPEECH:
        return ''
    return transcript


def describe_image_message(image_message: dict, key: dict) -> str:
    """Baixa a imagem da mensagem e devolve uma descrição objetiva em português."""
    base64_data, mimetype = download_media_base64(key)
    mimetype = _clean_mimetype(mimetype or image_message.get('mimetype'), _DEFAULT_IMAGE_MIME)

    prompt = _VISION_PROMPT
    caption = (image_message.get('caption') or '').strip()
    if caption:
        prompt = f'{prompt}\nLegenda enviada junto: "{caption}"'

    llm = get_llm(temperature=0.0, model=settings.OPENROUTER_VISION_MODEL)
    result = llm.invoke([
        HumanMessage(content=[
            {'type': 'text', 'text': prompt},
            {'type': 'image', 'base64': base64_data, 'mime_type': mimetype},
        ])
    ])

    return (result.content or '').strip()

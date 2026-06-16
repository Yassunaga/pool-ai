import logging

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Agent
from .serializers import AgentSerializer, ChatRequestSerializer, ChatResponseSerializer
from .services.chat_service import send_message
from .services.debounce_service import enqueue
from .services.evolution_service import send_text
from .services.media_service import describe_image_message, transcribe_audio_message

logger = logging.getLogger(__name__)

# Wrappers que aninham o conteúdo real em ``.message`` (efêmeras, "ver uma vez",
# documento com legenda). Descemos um nível para achar o áudio/imagem de verdade.
_WRAPPER_KEYS = (
    'ephemeralMessage',
    'viewOnceMessage',
    'viewOnceMessageV2',
    'viewOnceMessageV2Extension',
    'documentWithCaptionMessage',
)

# Fallbacks (POOL-16): mídia NUNCA pode resultar em silêncio para o cliente. Quando
# não conseguimos transcrever/interpretar (ou o tipo não é suportado), respondemos
# pedindo texto. Enviados direto pelo webhook (não dependem do debounce_worker).
_AUDIO_FALLBACK = (
    'Recebi seu áudio 🎧, mas não consegui ouvir agora. '
    'Consegue me mandar por texto? Aí já te ajudo 😊'
)
_IMAGE_FALLBACK = (
    'Recebi sua imagem 📷, mas não consegui abrir aqui. '
    'Me conta por texto o que você precisa que eu te ajudo!'
)
_VIDEO_FALLBACK = (
    'Recebi seu vídeo, mas não consigo assistir por aqui 🙏 '
    'Me manda por texto ou áudio que eu te ajudo!'
)
_DOCUMENT_FALLBACK = (
    'Recebi seu arquivo, mas não consigo abrir por aqui 🙏 '
    'Me conta por texto que eu te ajudo!'
)


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer


class ChatAPIView(APIView):
    def post(self, request):
        request_serializer = ChatRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        result = send_message(
            session_id=request_serializer.validated_data['session_id'],
            message=request_serializer.validated_data['message'],
        )

        response_serializer = ChatResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


def _unwrap_message(message: dict) -> dict:
    """Desce em wrappers (efêmera, ver-uma-vez, doc com legenda) até o conteúdo real."""
    seen = 0
    while seen < len(_WRAPPER_KEYS):
        for wrapper in _WRAPPER_KEYS:
            inner = (message.get(wrapper) or {}).get('message')
            if isinstance(inner, dict):
                message = inner
                break
        else:
            break
        seen += 1
    return message


def _extract_text(message: dict) -> str | None:
    """Pull the text body out of an Evolution message payload."""
    return message.get('conversation') or (
        message.get('extendedTextMessage') or {}
    ).get('text')


def _safe_reply(number: str, text: str) -> None:
    """Envia uma resposta direta, engolindo falhas (o webhook tem que devolver 200)."""
    try:
        send_text(number, text)
    except Exception:
        logger.exception('falha ao enviar resposta de mídia para %s', number)


def _handle_media(number: str, message: dict, key: dict) -> None:
    """Trata mídia (POOL-16): áudio e imagem viram texto no fluxo normal; demais
    tipos recebem um fallback pedindo texto. Garante que mídia nunca fica em silêncio.

    Tipos não-conteúdo (reações, stickers, mensagens de protocolo) são ignorados de
    propósito — responder a eles só geraria ruído.
    """
    if 'audioMessage' in message:
        try:
            transcript = transcribe_audio_message(message['audioMessage'], key)
        except Exception:
            logger.exception('falha ao transcrever áudio de %s', number)
            transcript = ''
        if transcript:
            enqueue(number, transcript)
        else:
            _safe_reply(number, _AUDIO_FALLBACK)
        return

    if 'imageMessage' in message:
        image_message = message['imageMessage'] or {}
        caption = (image_message.get('caption') or '').strip()
        try:
            description = describe_image_message(image_message, key)
        except Exception:
            logger.exception('falha ao interpretar imagem de %s', number)
            description = ''
        if description:
            note = f'[O cliente enviou uma imagem pelo WhatsApp. Conteúdo: {description}]'
            enqueue(number, f'{caption}\n{note}' if caption else note)
        elif caption:
            # Sem visão, mas a legenda já é texto útil: segue o fluxo normal.
            enqueue(number, caption)
        else:
            _safe_reply(number, _IMAGE_FALLBACK)
        return

    if 'videoMessage' in message:
        _safe_reply(number, _VIDEO_FALLBACK)
        return

    if 'documentMessage' in message:
        _safe_reply(number, _DOCUMENT_FALLBACK)
        return

    # Demais tipos (sticker, reação, protocolo): ignora silenciosamente.


class EvolutionWebhookAPIView(APIView):
    """Receive WhatsApp messages from Evolution, run the agent, reply back.

    Enqueues each inbound message into the Redis debounce buffer and returns
    200 immediately; the ``debounce_worker`` process groups burst messages into
    a single turn and replies. Always returns 200 so Evolution does not retry
    (which would re-run the graph and double-reply).
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # Token compartilhado na URL do webhook (?token=...). Vazio = sem checagem.
        expected = settings.EVOLUTION_WEBHOOK_TOKEN
        if expected and request.query_params.get('token') != expected:
            return Response(status=status.HTTP_403_FORBIDDEN)

        payload = request.data or {}
        logger.debug('evolution webhook payload: %s', payload)
        if str(payload.get('event', '')).lower() != 'messages.upsert':
            return Response(status=status.HTTP_200_OK)
        data = payload.get('data') or {}
        key = data.get('key') or {}

        # Skip our own outgoing messages, groups, and status broadcasts.
        if key.get('fromMe'):
            return Response(status=status.HTTP_200_OK)

        remote_jid = key.get('remoteJid') or ''
        if remote_jid.endswith('@g.us') or remote_jid == 'status@broadcast':
            return Response(status=status.HTTP_200_OK)

        number = remote_jid.split('@', 1)[0]
        if not number:
            return Response(status=status.HTTP_200_OK)

        message = _unwrap_message(data.get('message') or {})

        text = _extract_text(message)
        if text:
            # Enfileira; o debounce_worker agrupa rajadas e responde num só turno.
            enqueue(number, text)
            return Response(status=status.HTTP_200_OK)

        # Não é texto: pode ser áudio/imagem/outra mídia (POOL-16).
        _handle_media(number, message, key)

        return Response(status=status.HTTP_200_OK)

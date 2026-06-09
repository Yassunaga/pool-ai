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

logger = logging.getLogger(__name__)


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


def _extract_text(message: dict) -> str | None:
    """Pull the text body out of an Evolution message payload."""
    return message.get('conversation') or (
        message.get('extendedTextMessage') or {}
    ).get('text')


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
        payload = request.data or {}
        print(payload)
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

        # allowed = settings.EVOLUTION_ALLOWED_NUMBERS
        # if allowed and number not in allowed:
        #     return Response(status=status.HTTP_200_OK)

        text = _extract_text(data.get('message') or {})
        if not text:
            return Response(status=status.HTTP_200_OK)

        # Enfileira; o debounce_worker agrupa rajadas e responde num só turno.
        enqueue(number, text)

        return Response(status=status.HTTP_200_OK)

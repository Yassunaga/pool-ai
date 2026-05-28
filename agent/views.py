from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Agent
from .serializers import AgentSerializer, ChatRequestSerializer, ChatResponseSerializer
from .services.chat_service import send_message


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

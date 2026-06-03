from rest_framework import serializers

from .models import Agent


class AgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = ['id', 'name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatRequestSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=255)
    message = serializers.CharField()


class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    replies = serializers.ListField(child=serializers.CharField())

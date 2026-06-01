from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AgentViewSet, ChatAPIView, EvolutionWebhookAPIView

router = DefaultRouter()
router.register(r'agents', AgentViewSet, basename='agent')

urlpatterns = [
    path('agent/chat/', ChatAPIView.as_view(), name='agent-chat'),
    path('agent/webhook/evolution/', EvolutionWebhookAPIView.as_view(), name='evolution-webhook'),
    *router.urls,
]

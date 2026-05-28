from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AgentViewSet, ChatAPIView

router = DefaultRouter()
router.register(r'agents', AgentViewSet, basename='agent')

urlpatterns = [
    path('agent/chat/', ChatAPIView.as_view(), name='agent-chat'),
    *router.urls,
]

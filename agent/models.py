from django.db import models


class Agent(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Lead(models.Model):
    """Espelho (read model) do lead coletado pelo grafo, sincronizado a cada
    turno em ``chat_service.send_message``. A fonte de verdade continua sendo o
    checkpoint do LangGraph; este registro existe para o time enxergar os leads
    no admin e para controlar a notificação de handoff."""

    AREA_CHOICES = [('urban', 'Urbana'), ('rural', 'Rural')]

    session_id = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True, default='')
    area_type = models.CharField(max_length=10, choices=AREA_CHOICES, blank=True, default='')
    handoff_requested = models.BooleanField(default=False)
    handoff_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f'{self.name or "(sem nome)"} — {self.session_id}'

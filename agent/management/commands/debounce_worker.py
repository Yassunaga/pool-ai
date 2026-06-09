"""Worker que dreana sessões em debounce e dispara um único turno do agente.

Roda como processo separado (long-lived), independente de quantos web workers
existam:

    uv run python manage.py debounce_worker

Rode UMA instância. O drain por sessão é atômico, então rodar mais de uma é seguro
(drains concorrentes pegam lista vazia), mas o padrão é uma só.
"""

import logging
import time

from django.core.management.base import BaseCommand

from agent.services.chat_service import send_message
from agent.services.debounce_service import drain_due
from agent.services.evolution_service import send_text

logger = logging.getLogger(__name__)

POLL_INTERVAL = 1


class Command(BaseCommand):
    help = 'Dreana mensagens do WhatsApp em debounce e responde como um único turno.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('debounce_worker iniciado. Ctrl+C para parar.'))
        try:
            while True:
                self._tick()
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            self.stdout.write('\nEncerrando debounce_worker.')

    def _tick(self):
        try:
            ready = drain_due()
        except Exception:
            # Falha no Redis não pode derrubar o loop.
            logger.exception('debounce_worker: erro ao dreanar sessões')
            return

        for number, msgs in ready:
            # Roda fora do ciclo HTTP: exceção não-tratada = usuário sem resposta e
            # sem rastro. Isola cada sessão num try/except com logging.
            try:
                combined = '\n'.join(msgs)
                result = send_message(session_id=number, message=combined)
                for reply in result.get('replies') or []:
                    send_text(number, reply)
                logger.info('debounce flush %s (%d msgs)', number, len(msgs))
            except Exception:
                logger.exception('debounce_worker: erro ao processar sessão %s', number)
                raise

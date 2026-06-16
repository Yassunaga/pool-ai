"""Testes do webhook da Evolution, com foco no tratamento de mídia (POOL-16).

As chamadas de rede/LLM (download da mídia, transcrição, visão) são mockadas — os
testes cobrem o *roteamento* do webhook (o que vira enqueue, o que vira resposta
direta, o que é ignorado), não a qualidade da transcrição em si (isso é validação
manual com áudio real, conforme a tarefa)."""

from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


def _upsert(message: dict, *, number: str = '5511999999999', from_me: bool = False) -> dict:
    """Monta um payload messages.upsert da Evolution com a mensagem dada."""
    return {
        'event': 'messages.upsert',
        'data': {
            'key': {
                'remoteJid': f'{number}@s.whatsapp.net',
                'fromMe': from_me,
                'id': 'ABC123',
            },
            'message': message,
        },
    }


class EvolutionWebhookTextTests(TestCase):
    def setUp(self):
        self.url = reverse('evolution-webhook')

    @patch('agent.views.enqueue')
    def test_plain_text_is_enqueued(self, enqueue):
        resp = self.client.post(
            self.url, _upsert({'conversation': 'Oi, tudo bem?'}), content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_called_once_with('5511999999999', 'Oi, tudo bem?')

    @patch('agent.views.enqueue')
    def test_from_me_is_ignored(self, enqueue):
        resp = self.client.post(
            self.url, _upsert({'conversation': 'eco'}, from_me=True), content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_not_called()


class EvolutionWebhookAudioTests(TestCase):
    def setUp(self):
        self.url = reverse('evolution-webhook')

    @patch('agent.views.enqueue')
    @patch('agent.views.transcribe_audio_message', return_value='Quanto custa um poço?')
    def test_audio_transcription_is_enqueued(self, transcribe, enqueue):
        resp = self.client.post(
            self.url, _upsert({'audioMessage': {'mimetype': 'audio/ogg; codecs=opus'}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        transcribe.assert_called_once()
        enqueue.assert_called_once_with('5511999999999', 'Quanto custa um poço?')

    @patch('agent.views._safe_reply')
    @patch('agent.views.enqueue')
    @patch('agent.views.transcribe_audio_message', side_effect=RuntimeError('boom'))
    def test_audio_failure_falls_back_to_reply(self, transcribe, enqueue, safe_reply):
        resp = self.client.post(
            self.url, _upsert({'audioMessage': {}}), content_type='application/json'
        )
        # Critério de aceite: áudio NUNCA fica em silêncio.
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_not_called()
        safe_reply.assert_called_once()

    @patch('agent.views._safe_reply')
    @patch('agent.views.enqueue')
    @patch('agent.views.transcribe_audio_message', return_value='')
    def test_audio_without_speech_falls_back_to_reply(self, transcribe, enqueue, safe_reply):
        resp = self.client.post(
            self.url, _upsert({'audioMessage': {}}), content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_not_called()
        safe_reply.assert_called_once()


class EvolutionWebhookImageTests(TestCase):
    def setUp(self):
        self.url = reverse('evolution-webhook')

    @patch('agent.views.enqueue')
    @patch('agent.views.describe_image_message', return_value='Um terreno de chácara com vegetação.')
    def test_image_description_is_enqueued(self, describe, enqueue):
        resp = self.client.post(
            self.url, _upsert({'imageMessage': {'caption': 'meu terreno'}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_called_once()
        number, text = enqueue.call_args.args
        self.assertEqual(number, '5511999999999')
        self.assertIn('meu terreno', text)
        self.assertIn('terreno de chácara', text)

    @patch('agent.views._safe_reply')
    @patch('agent.views.enqueue')
    @patch('agent.views.describe_image_message', side_effect=RuntimeError('boom'))
    def test_image_failure_with_caption_enqueues_caption(self, describe, enqueue, safe_reply):
        resp = self.client.post(
            self.url, _upsert({'imageMessage': {'caption': 'segue a foto'}}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_called_once_with('5511999999999', 'segue a foto')
        safe_reply.assert_not_called()

    @patch('agent.views._safe_reply')
    @patch('agent.views.enqueue')
    @patch('agent.views.describe_image_message', side_effect=RuntimeError('boom'))
    def test_image_failure_without_caption_falls_back(self, describe, enqueue, safe_reply):
        resp = self.client.post(
            self.url, _upsert({'imageMessage': {}}), content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_not_called()
        safe_reply.assert_called_once()


class EvolutionWebhookOtherMediaTests(TestCase):
    def setUp(self):
        self.url = reverse('evolution-webhook')

    @patch('agent.views._safe_reply')
    @patch('agent.views.enqueue')
    def test_video_falls_back_to_reply(self, enqueue, safe_reply):
        resp = self.client.post(
            self.url, _upsert({'videoMessage': {}}), content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_not_called()
        safe_reply.assert_called_once()

    @patch('agent.views._safe_reply')
    @patch('agent.views.enqueue')
    def test_document_falls_back_to_reply(self, enqueue, safe_reply):
        resp = self.client.post(
            self.url, _upsert({'documentMessage': {}}), content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_not_called()
        safe_reply.assert_called_once()

    @patch('agent.views._safe_reply')
    @patch('agent.views.enqueue')
    def test_sticker_is_ignored_silently(self, enqueue, safe_reply):
        resp = self.client.post(
            self.url, _upsert({'stickerMessage': {}}), content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_not_called()
        safe_reply.assert_not_called()

    @patch('agent.views.transcribe_audio_message', return_value='áudio dentro de efêmera')
    @patch('agent.views.enqueue')
    def test_ephemeral_wrapper_is_unwrapped(self, enqueue, transcribe):
        payload = _upsert({'ephemeralMessage': {'message': {'audioMessage': {}}}})
        resp = self.client.post(self.url, payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        enqueue.assert_called_once_with('5511999999999', 'áudio dentro de efêmera')

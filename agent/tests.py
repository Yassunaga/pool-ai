from django.test import SimpleTestCase

from agent.graph.guardrail import (
    MAX_CHUNK_LEN,
    MONEY_RE,
    SAFE_FALLBACK,
    detect,
    sanitize,
)


class GuardrailDetectTests(SimpleTestCase):
    """Detecção determinística de violações nos chunks de resposta."""

    def test_unauthorized_money_is_flagged(self):
        v = detect(['O valor fica em torno de R$ 8.000,00'], money_allowed=False)
        self.assertTrue(v.money)
        self.assertTrue(v.any)

    def test_authorized_money_once_is_clean(self):
        v = detect(['A média fica em R$ 8.000,00, depende da avaliação'], money_allowed=True)
        self.assertFalse(v.money)
        self.assertFalse(v.any)

    def test_authorized_money_twice_is_flagged(self):
        v = detect(['R$ 8.000,00 hoje', 'mas amanhã pode ser R$ 9.000,00'], money_allowed=True)
        self.assertTrue(v.money)

    def test_hyphen_is_flagged(self):
        v = detect(['Bem-vindo à Natural Engenharia'], money_allowed=False)
        self.assertTrue(v.hyphen)

    def test_overlong_chunk_is_flagged(self):
        v = detect(['x' * (MAX_CHUNK_LEN + 1)], money_allowed=False)
        self.assertTrue(v.too_long)

    def test_clean_chunks_have_no_violation(self):
        v = detect(['Oi! Como posso te ajudar hoje?'], money_allowed=False)
        self.assertFalse(v.any)


class GuardrailSanitizeTests(SimpleTestCase):
    """Sanitização é a garantia final: o invariante vale mesmo se a regen falhar."""

    def test_unauthorized_money_is_stripped(self):
        out = sanitize(['Fica em torno de R$ 8.000,00, mas varia'], money_allowed=False)
        for chunk in out:
            self.assertIsNone(MONEY_RE.search(chunk), f'valor vazou em: {chunk!r}')

    def test_money_only_value_falls_back_to_safe_message(self):
        out = sanitize(['R$ 8.000,00'], money_allowed=False)
        self.assertEqual(out, [SAFE_FALLBACK])

    def test_authorized_money_is_preserved_once(self):
        out = sanitize(['A média fica em R$ 8.000,00, e depende da avaliação'], money_allowed=True)
        self.assertEqual(len(MONEY_RE.findall('\n'.join(out))), 1)

    def test_authorized_money_keeps_only_first(self):
        out = sanitize(['R$ 8.000,00 hoje', 'amanhã R$ 9.000,00'], money_allowed=True)
        self.assertEqual(len(MONEY_RE.findall('\n'.join(out))), 1)

    def test_hyphen_is_removed(self):
        out = sanitize(['Bem-vindo de volta'], money_allowed=False)
        self.assertNotIn('-', '\n'.join(out))

    def test_overlong_chunk_is_truncated(self):
        out = sanitize(['palavra ' * 200], money_allowed=False)
        for chunk in out:
            self.assertLessEqual(len(chunk), MAX_CHUNK_LEN)

    def test_clean_chunks_pass_through(self):
        chunks = ['Oi!', 'Como posso ajudar?']
        self.assertEqual(sanitize(chunks, money_allowed=False), chunks)

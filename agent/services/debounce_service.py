"""Debounce de mensagens do WhatsApp via Redis (compartilhado entre processos).

O webhook só enfileira (``enqueue``); um worker dedicado dreana as sessões cuja
janela expirou (``drain_due``) e dispara um único turno do agente.

Layout das chaves (todas no DB index de ``settings.REDIS_URL``):
- ``debounce:buffer:{number}`` (LIST) — textos acumulados, em ordem de chegada.
- ``debounce:pending``        (ZSET) — número -> deadline (epoch). Score sobrescrito
  a cada mensagem nova, empurrando o prazo enquanto o usuário digita.
"""

import time

import redis
from django.conf import settings

_BUFFER_PREFIX = 'debounce:buffer:'
_PENDING_KEY = 'debounce:pending'

# Drena uma sessão atomicamente. LRANGE + DEL precisam rodar juntos, senão uma
# mensagem que chega entre os dois é perdida. Também re-checa o deadline: se uma
# mensagem acabou de empurrar o prazo para o futuro, não dreana ainda.
_DRAIN_LUA = """
local buf = KEYS[1]
local pending = KEYS[2]
local number = ARGV[1]
local now = tonumber(ARGV[2])
local score = redis.call('ZSCORE', pending, number)
if not score or tonumber(score) > now then
  return {}
end
local msgs = redis.call('LRANGE', buf, 0, -1)
redis.call('DEL', buf)
redis.call('ZREM', pending, number)
return msgs
"""

_client = None
_drain = None


def _get_client() -> redis.Redis:
    global _client, _drain
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        _drain = _client.register_script(_DRAIN_LUA)
    return _client


def enqueue(number: str, text: str) -> None:
    """Acumula uma mensagem e (re)agenda o deadline da sessão."""
    client = _get_client()
    deadline = time.time() + settings.DEBOUNCE_SECONDS
    pipe = client.pipeline()
    pipe.rpush(f'{_BUFFER_PREFIX}{number}', text)
    pipe.zadd(_PENDING_KEY, {number: deadline})
    pipe.execute()


def drain_due() -> list[tuple[str, list[str]]]:
    """Retorna ``(number, [mensagens])`` para cada sessão cuja janela expirou.

    O drain por sessão é atômico (script Lua). Sessões cujo deadline foi empurrado
    para o futuro entre o ``ZRANGEBYSCORE`` e o script retornam vazio e são puladas.
    """
    client = _get_client()
    now = time.time()
    due_numbers = client.zrangebyscore(_PENDING_KEY, 0, now)

    drained: list[tuple[str, list[str]]] = []
    for number in due_numbers:
        msgs = _drain(
            keys=[f'{_BUFFER_PREFIX}{number}', _PENDING_KEY],
            args=[number, now],
        )
        if msgs:
            drained.append((number, list(msgs)))
    return drained

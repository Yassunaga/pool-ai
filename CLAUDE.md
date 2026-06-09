# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Dependencies are managed with `uv` (see `pyproject.toml`, `uv.lock`). Python 3.13+.

```bash
# Install / sync deps
uv sync

# Run any command inside the project venv
uv run <cmd>

# Django dev server (host:8000)
uv run python manage.py runserver

# Migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# Interactive REPL against the LangGraph sales agent
uv run python manage.py chat                       # new session
uv run python manage.py chat --session-id foo      # resume thread "foo"
uv run python manage.py chat --show-state          # print collected_data each turn

# Evolution API (WhatsApp) — separate stack
cd evolution-api && docker compose up -d

# Debounce worker — MUST run alongside the web server for WhatsApp replies
uv run python manage.py debounce_worker
```

There is no test runner wired up yet (`agent/tests.py` is empty).

## Architecture

This is a Django + DRF backend wrapping a **LangGraph** conversational sales agent for Natural Engenharia (artesian well drilling, Portuguese-language). The agent runs as a state machine with SQLite-backed checkpointing, and can be driven via either a REST endpoint or a WhatsApp webhook.

### Two storage layers (don't confuse them)

- `db.sqlite3` — Django ORM (just the `Agent` model in `agent/models.py`).
- `langgraph_state.sqlite` — LangGraph thread checkpointer, opened directly via `sqlite3.connect(settings.LANGGRAPH_DB_PATH)` in `agent/graph/graph.py`. This is where per-`session_id` conversation state lives (messages, `collected_data`, `is_greeted`, `workflow_step`). Path is set in `config/settings.py` as `LANGGRAPH_DB_PATH`.

### Request → graph flow

Both entry points funnel through `agent/services/chat_service.py::send_message(session_id, message)`, which calls `graph.invoke(...)` with `config={'configurable': {'thread_id': session_id}}` and then collects the **tail run of `AIMessage`s** from the result as `replies` (a single turn can emit multiple messages, as the `greetings` node does).

- `POST /api/agent/chat/` (`ChatAPIView`) — JSON `{session_id, message}` in, `{session_id, replies, collected_data, workflow_step}` out.
- `POST /api/agent/webhook/evolution/` (`EvolutionWebhookAPIView`) — WhatsApp inbound. Filters out `fromMe`, group (`@g.us`), and `status@broadcast` messages, derives `session_id` from the sender's number (`remoteJid.split('@')[0]`), then **enqueues the text into the Redis debounce buffer** (`agent/services/debounce_service.py::enqueue`) and returns immediately. It does **not** run the graph inline. **Always returns 200**, even on failure, so Evolution doesn't retry and double-run the graph.

### Message debounce (WhatsApp burst grouping)

Burst messages from one number ("Oi" + "tudo bem?") must be answered as a single turn. Because production runs **multiple web workers**, the buffer can't live in process memory — it lives in Redis (`agent/services/debounce_service.py`), reusing the Evolution Redis isolated on **DB index 1** (keys prefixed `debounce:`).

- Webhook → `enqueue(number, text)`: `RPUSH debounce:buffer:{number}` + `ZADD debounce:pending {now + DEBOUNCE_SECONDS}` (the deadline is pushed forward on every new message).
- `manage.py debounce_worker` (separate long-lived process, run **one** instance) polls every 0.5s, and for each session whose window elapsed drains the buffer **atomically via a Lua script** (`LRANGE`+`DEL`+`ZREM` + deadline re-check — prevents lost messages on the window boundary), joins the texts with `\n` into a single `HumanMessage`, runs the graph via `send_message`, and posts replies via `send_text`. Each session is processed in its own `try/except` because it runs outside the HTTP cycle. **The worker must be running or WhatsApp replies never get sent.**

### Evolution API (WhatsApp) integration

Evolution runs in Docker at `localhost:8080` (`evolution-api/docker-compose.yml`: evolution-api + postgres + redis). Django runs on the host at `:8000`. Critical gotcha: for the container's webhook to reach Django, the webhook URL must use `host.docker.internal:8000`, **not** `localhost`. `host.docker.internal` is already in `ALLOWED_HOSTS` (`config/settings.py`) — keep it there or Django 400s with `DisallowedHost`.

`EVOLUTION_ALLOWED_NUMBERS` (comma-separated env var) gates which sender numbers get replies; empty = everyone. The allowlist check in `EvolutionWebhookAPIView` is currently commented out — re-enable before exposing.

### Settings / env

`.env` is loaded in `config/settings.py` via `python-dotenv`. Required: `OPENAI_API_KEY`. Optional with defaults: `OPENAI_MODEL` (`gpt-4o-mini`), `EVOLUTION_API_URL` (`http://localhost:8080`), `EVOLUTION_INSTANCE` (`Local`), `EVOLUTION_API_KEY`, `EVOLUTION_ALLOWED_NUMBERS`. See `.env.example`.

### Rules
- Prefer using pydantic models over TypedDict for LangGraph.
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
- `langgraph_state.sqlite` — LangGraph thread checkpointer, opened directly via `sqlite3.connect(settings.LANGGRAPH_DB_PATH)` in `agent/graph/graph.py`. This is where per-`session_id` conversation state lives: `ConversationState` (`agent/graph/models.py`) holds `messages` plus `lead` — a `Lead` pydantic model with `name` and `area_type` (`'urban' | 'rural'`). Path is set in `config/settings.py` as `LANGGRAPH_DB_PATH`. Gotcha: custom pydantic models stored in the checkpoint must be allowlisted in `_ALLOWED_MSGPACK_MODULES` in `agent/graph/graph.py` (currently just `Lead`) or (de)serialization fails.

### Request → graph flow

Both entry points funnel through `agent/services/chat_service.py::send_message(session_id, message)`, which calls `graph.invoke(...)` with `config={'configurable': {'thread_id': session_id}}` and then collects the **tail run of `AIMessage`s** from the result as `replies` (a single turn emits multiple messages because the `agent` node splits its answer into `ChunkedReply` chunks — see below). It returns only `{session_id, replies}`.

- `POST /api/agent/chat/` (`ChatAPIView`) — JSON `{session_id, message}` in, `{session_id, replies}` out (shaped by `ChatResponseSerializer` in `agent/serializers.py`).
- `POST /api/agent/webhook/evolution/` (`EvolutionWebhookAPIView`) — WhatsApp inbound. Filters out `fromMe`, group (`@g.us`), and `status@broadcast` messages, derives `session_id` from the sender's number (`remoteJid.split('@')[0]`), then **enqueues the text into the Redis debounce buffer** (`agent/services/debounce_service.py::enqueue`) and returns immediately. It does **not** run the graph inline. **Always returns 200**, even on failure, so Evolution doesn't retry and double-run the graph.

### The graph (agent/graph/)

Two nodes, linear: `START → extract → agent → END` (`agent/graph/graph.py`, lazy thread-safe singleton via `get_graph()`).

- `extract` (`agent/graph/nodes.py`) — structured-output LLM call (temperature 0.0) that fills the `Lead` fields from the whole conversation; only non-null values overwrite, so already-collected data is never erased.
- `agent` — runs an internal ReAct loop via `create_agent` with tools `greeting_instructions`, `retrieve_lead_information`, and `build_budget` (`agent/graph/tools.py` — the latter two are closures bound to the current `lead`, since the inner loop only sees messages). Only the final answer returns to state, as a `ChunkedReply` (1–3 short chunks via `response_format`), each chunk becoming its own `AIMessage` so WhatsApp delivery mimics a person typing in sequence.
- LLM factory lives in `agent/graph/llm.py` (`langchain_openrouter.ChatOpenRouter`), shared by both nodes.
- `agent/graph/faq.py` — the FAQ, the agent's **single source of truth for factual questions** about the company (costs, fees, deadlines, warranties, coverage, policies). `render_faq()` injects it into the agent system prompt (`KNOWN_FACTS` in `agent/graph/prompts.py`); anything not answered there the agent must defer to the human specialist instead of improvising. To change a factual answer, edit `faq.py` — not the prompt. Entries marked `[CONFIRMAR]` are safe placeholders awaiting the real business policy.

### Message debounce (WhatsApp burst grouping)

Burst messages from one number ("Oi" + "tudo bem?") must be answered as a single turn. Because production runs **multiple web workers**, the buffer can't live in process memory — it lives in Redis (`agent/services/debounce_service.py`), reusing the Evolution Redis isolated on **DB index 1** (keys prefixed `debounce:`).

- Webhook → `enqueue(number, text)`: `RPUSH debounce:buffer:{number}` + `ZADD debounce:pending {now + DEBOUNCE_SECONDS}` (the deadline is pushed forward on every new message).
- `manage.py debounce_worker` (separate long-lived process, run **one** instance) polls every 0.5s, and for each session whose window elapsed drains the buffer **atomically via a Lua script** (`LRANGE`+`DEL`+`ZREM` + deadline re-check — prevents lost messages on the window boundary), joins the texts with `\n` into a single `HumanMessage`, runs the graph via `send_message`, and posts replies via `send_text`. Each session is processed in its own `try/except` because it runs outside the HTTP cycle. **The worker must be running or WhatsApp replies never get sent.**

### Evolution API (WhatsApp) integration

Evolution runs in Docker at `localhost:8080` (`evolution-api/docker-compose.yml`: evolution-api + postgres + redis). Django runs on the host at `:8000`. Critical gotcha: for the container's webhook to reach Django, the webhook URL must use `host.docker.internal:8000`, **not** `localhost`. `host.docker.internal` is already in `ALLOWED_HOSTS` (`config/settings.py`) — keep it there or Django 400s with `DisallowedHost`.

`EVOLUTION_ALLOWED_NUMBERS` (comma-separated env var) gates which sender numbers get replies; empty = everyone. The allowlist check in `EvolutionWebhookAPIView` is currently commented out — re-enable before exposing.

### Settings / env

`.env` is loaded in `config/settings.py` via `python-dotenv`. Required: `OPENROUTER_API_KEY`. Optional with defaults: `OPENROUTER_MODEL` (`anthropic/claude-sonnet-4-6`), `OPENROUTER_BASE_URL` (`https://openrouter.ai/api/v1`), `EVOLUTION_API_URL` (`http://localhost:8080`), `EVOLUTION_INSTANCE` (`Local`), `EVOLUTION_API_KEY`, `EVOLUTION_ALLOWED_NUMBERS`, `EVOLUTION_TYPING_MS_PER_CHAR` (`30` — "digitando…" presence lasts `len(text) * N` ms before each send; `0` disables), `REDIS_URL` (`redis://localhost:6379/1`), `DEBOUNCE_SECONDS` (`8`). See `.env.example`.

### Rules
- Prefer using pydantic models over TypedDict for LangGraph.
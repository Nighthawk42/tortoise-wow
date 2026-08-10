# Tortoise AI sidecar

This directory contains the first standalone dialogue-sidecar slice. It loads
validated player profiles and roster bindings, resolves exactly one simulated
player for each request, and returns only a bounded `chat.text` candidate.

The scaffold deliberately uses a deterministic mock provider. It proves the
HTTP and personality boundary without provider credentials, model costs, game
server changes, or network calls from Eluna.

## Run locally

```powershell
cd sidecar
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8100
```

Then inspect `GET /health/live` and `GET /health/ready`. The sample dialogue
request under `tests/fixtures/dialogue-request.json` can be sent to
`POST /v1/dialogue`.

Configuration defaults to `sidecar/config`. Environment variable names and
safe development defaults are listed in `.env.example`. Provider credentials
must never be placed in persona YAML, roster bindings, MaNGOS configuration, or
committed environment files.

## Validate

```powershell
uv run ruff check .
uv run pytest
```

The next implementation slice adds the OpenAI-compatible provider adapter and
prompt compiler behind the existing `DialogueProvider` protocol. The bounded
C++ gateway follows only after this standalone contract remains reliable under
timeouts, invalid responses, and load.


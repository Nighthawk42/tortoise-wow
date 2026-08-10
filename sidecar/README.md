# Tortoise AI sidecar

This directory contains the first standalone dialogue-sidecar slice. It loads
validated player profiles and roster bindings, resolves exactly one simulated
player for each request, and returns only a bounded `chat.text` candidate.

The default remains a deterministic mock provider. An asynchronous
OpenAI-compatible adapter is also available for OpenRouter, OpenCode-compatible
endpoints, and self-hosted servers. Provider credentials stay entirely in the
sidecar process.

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

## OpenRouter free-model smoke test

`config/providers.yaml` maps the logical `dialogue-small` profile used by
personas to `openrouter/free`. The profile mapping contains no credentials.
For a local installation, copy the ignored environment template and add the
user's own provider key:

```powershell
Copy-Item .env.example .env
# Edit .env: select openrouter and set OPENROUTER_API_KEY.
uv run python -m scripts.provider_smoke
```

The sidecar reads `sidecar/.env` without copying its values into the global
process environment. Existing environment variables take precedence. Production
operators can instead inject the same names with a service manager, container
secret, or `TORTOISE_SIDECAR_ENV_FILE` pointing to a separately protected file.
The launcher requires no secret-manager-specific application.

For a self-hosted OpenAI-compatible endpoint, set the provider to
`openai-compatible`, set `TORTOISE_LLM_API_BASE`, and change the model route in
`config/providers.yaml`. `TORTOISE_LLM_MODEL` can temporarily override the
configured route for smoke testing. An API key is optional for local endpoints.

The prompt compiler creates a fresh bounded request for exactly one resolved
persona. It includes only that bot's materialized personality, current game
snapshot, recent dialogue, and supplied facts; it never sends the full roster.

## Validate

```powershell
uv run ruff check .
uv run pytest
```

The bounded C++ gateway follows after this standalone contract remains reliable
against the selected provider under representative concurrency and latency.

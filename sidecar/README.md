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
Run the smoke test with an ephemeral Bitwarden injection:

```powershell
$env:TORTOISE_SIDECAR_PROVIDER = "openrouter"
$env:TORTOISE_LLM_TIMEOUT_SECONDS = "45"
bwsx exec --secret OPENROUTER_API_KEY=OpenRouter -- `
  uv run python -m scripts.provider_smoke
```

Replace `OpenRouter` with the secret alias shown by `bwsx list`. Nothing is
written to `.env`, the shell command line, provider logs, or MaNGOS config.

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

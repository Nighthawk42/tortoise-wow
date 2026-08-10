# LLM provider adapter and prompt compiler

## Decision

The first live provider is a small asynchronous OpenAI-compatible adapter in
the Python sidecar. It works with OpenRouter, OpenCode Zen's compatible models,
and self-hosted endpoints by changing process configuration rather than persona
files or MaNGOS code.

The adapter stays behind `DialogueProvider`. Mozilla `any-llm` remains a viable
future implementation of that protocol when its additional provider-specific
normalization provides measurable value. It is not required for the first
vertical slice because the selected services already expose compatible chat
completion endpoints and the project needs a narrow, auditable failure boundary.

## One character per request

The sidecar does not send every profile to a model. For each dialogue request it:

1. verifies the server, realm, character GUID, expected name, and roster binding;
2. resolves one handcrafted profile or one stable archetype materialization;
3. compiles that persona with the bot snapshot, speaker, recent dialogue, and
   server-supplied facts;
4. sends two messages—a trusted system instruction and JSON conversation
   context—to one configured model route; and
5. accepts only one bounded plain-text `chat.text` result.

This shape stays constant whether ten or thousands of personas exist. Scale is
controlled by request admission and concurrency rather than prompt size.

## Configuration and secrets

`sidecar/config/providers.yaml` maps logical persona model profiles, currently
`dialogue-small`, to concrete model identifiers. It contains no credentials.
`TORTOISE_LLM_MODEL` can override a route for an operational smoke test.

Provider credentials are read only by the sidecar. The normal local installation
flow copies the ignored template and supplies the user's own key:

```powershell
Copy-Item sidecar/.env.example sidecar/.env
# Edit sidecar/.env, then start the sidecar or dashboard normally.
```

Process environment variables override `.env`. Deployments can use a service
manager, container secrets, or `TORTOISE_SIDECAR_ENV_FILE` for a separately
protected file. No particular secret manager is required. When the dashboard
does receive an injected key, it passes known LLM credential variables only to
the sidecar and strips them from MariaDB, `realmd`, `mangosd`, and the database
administration process.

## Failure behavior

The adapter enforces both the core-supplied request deadline and a shorter local
provider timeout. It propagates cancellation, caps simultaneous calls, rejects
requests above a sliding one-minute limit, and treats HTTP failures or malformed
response shapes as typed failures. The sidecar never retries past the request
deadline.

Structured health metrics report request, success, timeout, rate-limit, invalid
response, unavailable, cancellation, in-flight, peak concurrency, and average
latency counts without including prompt text or credentials.

## Free-provider validation

The adapter has been exercised against OpenCode Zen's `mimo-v2.5-free` endpoint
with an ephemeral process-injected credential. OpenRouter's documented `openrouter/free`
route is the default model mapping. Free routers are suitable for development,
but their availability, selected model, latency, and rate limits can vary; the
deterministic mock remains the default for tests.

Useful provider references:

- [OpenRouter free-model router](https://openrouter.ai/docs/guides/routing/routers/free-router)
- [OpenCode Zen endpoints](https://opencode.ai/docs/zen)
- [Mozilla any-llm](https://github.com/mozilla-ai/any-llm)
